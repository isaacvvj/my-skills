[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string[]]$InputFile,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputDirectory,

    [string]$Image = 'ghcr.io/opentechil/markitdown-for-ai:latest',

    [string]$ProjectRoot
)

$allowedExtensions = @('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.html', '.htm')
$runtime = if (Get-Command docker -ErrorAction SilentlyContinue) {
    'docker'
} elseif (Get-Command podman -ErrorAction SilentlyContinue) {
    'podman'
} else {
    throw '未找到 Docker 或 Podman。请安装并启动其中一个运行时，或保留资料索引并将此项标记为待转换。'
}

# 固定外部命令（docker/podman）输出解码为 UTF-8，避免 markitdown 转换的中文内容被按本地代码页（如 GBK）解码而乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
$resolvedProjectRoot = $null
if ($ProjectRoot) {
    $resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path.TrimEnd('\')
}

if ($PSCmdlet.ShouldProcess($resolvedOutput, '创建 Markdown 转换输出目录')) {
    New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
}

foreach ($candidate in $InputFile) {
    $source = Get-Item -LiteralPath $candidate -ErrorAction Stop
    if ($source.PSIsContainer) {
        throw "不支持目录输入：$($source.FullName)。请先在资料清单中选择明确的文件。"
    }
    if ($allowedExtensions -notcontains $source.Extension.ToLowerInvariant()) {
        throw "不支持的资料格式：$($source.FullName)"
    }

    $sourcePath = $source.FullName
    if ($resolvedProjectRoot) {
        if (-not $source.FullName.StartsWith($resolvedProjectRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "资料文件不在 ProjectRoot 内：$($source.FullName)"
        }
        $sourcePath = $source.FullName.Substring($resolvedProjectRoot.Length).TrimStart('\').Replace('\', '/')
    }

    $sha256 = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
    $hashPrefix = $sha256.Substring(0, 12).ToLowerInvariant()
    $target = Join-Path $resolvedOutput ("{0}-{1}.md" -f $source.BaseName, $hashPrefix)
    if (-not $PSCmdlet.ShouldProcess($source.FullName, "使用 $runtime 转换为 $target")) {
        continue
    }

    $mount = "{0}:/data:ro" -f $source.DirectoryName
    $converted = & $runtime run --rm -v $mount -w /data $Image $source.Name 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "文档转换失败：$($source.FullName)`n$($converted -join [Environment]::NewLine)"
    }

    $frontMatter = @(
        '---',
        'type: 原始资料转换稿',
        'status: 自动转换',
        'trust_level: L0',
        "source_path: $sourcePath",
        "source_sha256: $sha256",
        'verification_scope: 未验证',
        '---',
        ''
    )
    # 统一以 UTF-8 无 BOM 写出，保证 Obsidian 正常解析，同时避免 Git 差异和跨工具兼容问题
    $mdContent = @($frontMatter + $converted) -join [Environment]::NewLine
    [System.IO.File]::WriteAllText($target, $mdContent, [System.Text.UTF8Encoding]::new($false))
    Write-Host "[OK] $($source.Name) -> $target"
}
