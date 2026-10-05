<#
.SYNOPSIS
    gemini-bypass-permission installer for Windows.

.DESCRIPTION
    Installs a safe file editing tool for AI coding agents, plus the agent
    instructions (rules and skill) that make the agent actually use it.

    What it does:
      1. Verifies Python 3.8+
      2. Installs agent_edit.py to <prefix>/tools/
      3. Installs the rule to <prefix>/config/rules/agent-edit-safe.md
         (Antigravity global modular rule, always active)
      4. Installs the skill to <prefix>/config/skills/agent-edit-safe/
         (Antigravity 2.0 skill location)
      5. Installs the skill to ~/.claude/skills/agent-edit-safe/
         (Claude Code and older Antigravity compatibility)
      6. Appends a pointer to <prefix>/GEMINI.md
      7. Runs a real edit as a smoke test

.EXAMPLE
    irm https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.ps1 | iex

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    .\install.ps1 -Prefix C:\tools\gemini

.EXAMPLE
    .\install.ps1 -ProjectRoot C:\src\myproject

.EXAMPLE
    .\install.ps1 -NoSkill -NoRule
#>
[CmdletBinding()]
param(
    # Install into a different directory instead of $HOME\.gemini
    [string]$Prefix = "$HOME\.gemini",

    # Also add the rules to this project's workspace rules
    [string]$ProjectRoot,

    # Skip the skill files
    [switch]$NoSkill,

    # Skip the rule file
    [switch]$NoRule,

    # Do not touch GEMINI.md
    [switch]$NoGeminiMd
)

$ErrorActionPreference = 'Stop'
$RepoBase = 'https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main'
$RepoUrl = 'https://github.com/lepotane/gemini-bypass-permission'

# When this script is piped through Invoke-Expression there is no script file on
# disk, so $PSScriptRoot and $MyInvocation.MyCommand.Path are both null. Every
# use of $SrcDir below is guarded so the script falls back to downloading from
# GitHub instead of failing with "Cannot bind argument to parameter Path".
$SrcDir = $null
if ($PSScriptRoot) { $SrcDir = $PSScriptRoot }
elseif ($MyInvocation.MyCommand.Path) { $SrcDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$RunningFromFile = [bool]$SrcDir

function Write-Step  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "    $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "    $m" -ForegroundColor Yellow }
function Write-Fail  { param($m) Write-Host "    $m" -ForegroundColor Red }

# --------------------------------------------------------------- python check
Write-Step "Checking Python"

$python = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
        $v = & $candidate -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) {
            $parts = $v.Trim().Split('.')
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 8) {
                $python = $candidate
                Write-Ok "Found $candidate (Python $v)"
                break
            }
        }
    } catch { }
}

if (-not $python) {
    Write-Fail "Python 3.8+ not found."
    Write-Host ""
    Write-Host "  Install Python:" -ForegroundColor Yellow
    Write-Host "    1. Download from https://www.python.org/downloads/"
    Write-Host "    2. During setup, tick 'Add python.exe to PATH'"
    Write-Host "    3. Reopen PowerShell and run this again"
    Write-Host ""
    exit 1
}

# --------------------------------------------------------------- locate files
Write-Step "Locating files"

$toolSrc = if ($RunningFromFile) { Join-Path $SrcDir 'scripts\agent_edit.py' } else { $null }
$ruleSrc = if ($RunningFromFile) { Join-Path $SrcDir 'rules\agent-edit-safe.md' } else { $null }
$skillSrc = if ($RunningFromFile) { Join-Path $SrcDir 'skills\agent-edit-safe' } else { $null }

if (-not $RunningFromFile -or -not (Test-Path $toolSrc)) {
    Write-Warn "Not running from a checkout, downloading..."
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("gpb_" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $toolSrc = Join-Path $tmp 'agent_edit.py'
    try {
        Invoke-WebRequest -Uri "$RepoBase/scripts/agent_edit.py" -OutFile $toolSrc -UseBasicParsing
        Write-Ok "agent_edit.py"
    } catch {
        Write-Fail "Download failed: $($_.Exception.Message)"
        exit 1
    }
    if (-not $NoRule) {
        $dl = Join-Path $tmp 'agent-edit-safe.md'
        try {
            Invoke-WebRequest -Uri "$RepoBase/rules/agent-edit-safe.md" -OutFile $dl -UseBasicParsing
            $ruleSrc = $dl
            Write-Ok "agent-edit-safe.md"
        } catch { Write-Warn "Could not fetch the rule file" }
    }
}

# -------------------------------------------------------------------- install
Write-Step "Installing to $Prefix"

$toolsDir  = Join-Path $Prefix 'tools'
$rulesDir  = Join-Path $Prefix 'config\rules'
$skillsDir = Join-Path $Prefix 'config\skills'
$backupDir = Join-Path $Prefix 'backups'

foreach ($d in @($toolsDir, $backupDir)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

$destTool = Join-Path $toolsDir 'agent_edit.py'
Copy-Item $toolSrc $destTool -Force
Write-Ok "tool  : $destTool"

if (-not $NoRule) {
    if ($ruleSrc -and (Test-Path $ruleSrc)) {
        New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
        $destRule = Join-Path $rulesDir 'agent-edit-safe.md'
        Copy-Item $ruleSrc $destRule -Force
        Write-Ok "rule  : $destRule"
    } else {
        Write-Warn "rule file not found, skipped"
    }
}

if (-not $NoSkill) {
    # Antigravity 2.0 skill location
    $destSkill = Join-Path $skillsDir 'agent-edit-safe'
    New-Item -ItemType Directory -Force -Path (Join-Path $destSkill 'scripts') | Out-Null
    Copy-Item $destTool (Join-Path $destSkill 'scripts\agent_edit.py') -Force
    if ($skillSrc -and (Test-Path (Join-Path $skillSrc 'SKILL.md'))) {
        Copy-Item (Join-Path $skillSrc 'SKILL.md') (Join-Path $destSkill 'SKILL.md') -Force
    } else {
        try {
            Invoke-WebRequest -Uri "$RepoBase/skills/agent-edit-safe/SKILL.md" `
                -OutFile (Join-Path $destSkill 'SKILL.md') -UseBasicParsing
        } catch { Write-Warn "Could not fetch SKILL.md" }
    }
    Write-Ok "skill : $destSkill"

    # Claude Code and older Antigravity compatibility location
    $claudeSkill = Join-Path $HOME '.claude\skills\agent-edit-safe'
    try {
        New-Item -ItemType Directory -Force -Path (Join-Path $claudeSkill 'scripts') -ErrorAction Stop | Out-Null
        Copy-Item $destTool (Join-Path $claudeSkill 'scripts\agent_edit.py') -Force
        if (Test-Path (Join-Path $destSkill 'SKILL.md')) {
            Copy-Item (Join-Path $destSkill 'SKILL.md') (Join-Path $claudeSkill 'SKILL.md') -Force
        }
        Write-Ok "skill : $claudeSkill  (compat)"
    } catch {
        Write-Warn "Could not install to .claude\skills (skipped)"
    }
}

# ------------------------------------------------------------------ GEMINI.md
if (-not $NoGeminiMd) {
    $geminiMd = Join-Path $Prefix 'GEMINI.md'
    $existing = if (Test-Path $geminiMd) { Get-Content $geminiMd -Raw } else { '' }

    if ($existing -match 'agent-edit-safe') {
        Write-Ok "GEMINI.md already references agent-edit-safe (left untouched)"
    } else {
        $snippet = @"

---

# File editing protocol

Mandatory: modify files with the safe editing tool, never with built-in editor
tools. Full instructions are installed as an always-active rule.

- Tool: $destTool
- Rule: $(Join-Path $rulesDir 'agent-edit-safe.md')
- Start with: python $destTool --help

See $RepoUrl
"@
        $new = if ($existing) { $existing.TrimEnd() + "`n" + $snippet } else { $snippet.TrimStart() }
        Set-Content -Path $geminiMd -Value $new -Encoding UTF8 -NoNewline
        Write-Ok "GEMINI.md updated with a pointer"
    }
}

# ------------------------------------------------------------- workspace rule
if ($ProjectRoot) {
    Write-Step "Installing workspace rule into $ProjectRoot"
    $wsRules = Join-Path $ProjectRoot '.agents\rules'
    try {
        if (-not $ruleSrc -or -not (Test-Path $ruleSrc)) { throw 'rule file not available locally' }
        New-Item -ItemType Directory -Force -Path $wsRules | Out-Null
        Copy-Item $ruleSrc (Join-Path $wsRules 'agent-edit-safe.md') -Force
        Write-Ok "workspace rule: $wsRules\agent-edit-safe.md"
    } catch {
        Write-Warn "Could not install workspace rule: $($_.Exception.Message)"
    }
}

# --------------------------------------------------------------------- verify
Write-Step "Verifying"

$help = & $python $destTool --help 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Tool failed to run:"
    $help | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
    exit 1
}
Write-Ok "tool runs correctly"

$smoke = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbtest_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $smoke | Out-Null
$smokeFile = Join-Path $smoke 'sample.cpp'
[System.IO.File]::WriteAllText($smokeFile, "int smoke = 1;`r`n", (New-Object System.Text.UTF8Encoding($false)))
& $python $destTool --path $smokeFile --find 'smoke = 1' --replace 'smoke = 2' 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0 -and (Select-String -Path $smokeFile -Pattern 'smoke = 2' -Quiet)) {
    Write-Ok "smoke test passed (edit applied)"
} else {
    Write-Warn "smoke test inconclusive, but --help worked"
}
Remove-Item $smoke -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $backupDir -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "----------------------------------------------------------" -ForegroundColor Green
Write-Host " Installed." -ForegroundColor Green
Write-Host ""
Write-Host " Quick test:" -ForegroundColor Cyan
Write-Host "   $python `"$destTool`" --help"
Write-Host ""
Write-Host " IMPORTANT -- restart your agent." -ForegroundColor Yellow
Write-Host " Agents read rules and skills when a conversation starts." -ForegroundColor Yellow
Write-Host " An already running session keeps its old instructions." -ForegroundColor Yellow
Write-Host ""
Write-Host " If the agent still asks for confirmation:" -ForegroundColor Cyan
Write-Host "   1. Start a brand new conversation (not just a new message)"
Write-Host "   2. Check the Customizations > Rules panel lists the rule"
Write-Host "   3. Check the Customizations > Skills panel lists the skill"
Write-Host ""
Write-Host " Rollback support:" -ForegroundColor Cyan
Write-Host "   $python `"$destTool`" --rollback-list"
Write-Host ""
Write-Host " Uninstall:" -ForegroundColor Cyan
Write-Host "   Remove-Item -Recurse `"$destTool`", `"$(Join-Path $rulesDir 'agent-edit-safe.md')`", `"$(Join-Path $skillsDir 'agent-edit-safe')`""
Write-Host "   Remove-Item -Recurse `"$(Join-Path $HOME '.claude\skills\agent-edit-safe')`""
Write-Host ""
Write-Host " Docs: $RepoUrl" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------" -ForegroundColor Green
Write-Host ""