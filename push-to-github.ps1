param (
    [string]$CommitMessage = "Update to package",
    [bool]$Tag = $false,
    [string]$TagName = "0.0.0",
    [bool]$Fake = $false
)

if ($TagName -ne "0.0.0") {
    $Tag = $true
}

$ProjectName = "wagtail_fedit"


npx webpack

if ($Fake) {
    Write-Host "Fake mode enabled, exiting... (not pushing)"
    exit
}


function IsNumeric ($Value) {
    return $Value -match "^[\d\.]+$"
}

Function GITHUB_Upload {
    param (
        [parameter(Mandatory=$false)]
        [string]$Version
    )

    git add .
    if ($Tag) {
        $gitVersion = "v${Version}"
        git commit -m $CommitMessage
        git tag $gitVersion
        git push -u origin main --tags
    } else {
        git commit -m $CommitMessage
        git push -u origin main
    }
}

Function _NextVersionString {
    param (
        [string]$Version
    )

    $versionParts = $version -split "\."

    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    $patch = [int]$versionParts[2] + 1
    
    # validate integers
    if (-not (IsNumeric $major) -or -not (IsNumeric $minor) -or -not (IsNumeric $patch)) {
        Write-Host "Invalid version format"
        throw "Invalid version format"
    }

    if ($patch -gt 9) {
        $patch = 0
        $minor += 1
    }

    if ($minor -gt 9) {
        $minor = 0
        $major += 1
    }

    $newVersion = "$major.$minor.$patch"

    return $newVersion
}

function PYPI_NextVersion {
    param (
        [string]$ConfigFile = ".\setup.cfg"
    )
    # Read file content
    $fileContent = Get-Content -Path $ConfigFile

    # Extract the version, increment it, and prepare the updated version string
    $versionLine = $fileContent | Where-Object { $_ -match "version\s*=" }
    $version = $versionLine -split "=", 2 | ForEach-Object { $_.Trim() } | Select-Object -Last 1
    $newVersion = _NextVersionString -Version $version
    return $newVersion
}

function InitRepo {
    param (
        [string]$ConfigFile = ".\setup.cfg"
    )
    Write-Host "Initialising repository..."
    git init | Out-Host
    git add . | Out-Host
    git branch -M main | Out-Host
    git remote add origin "git@github.com:Nigel2392/${ProjectName}.git" | Out-Host
    $version = PYPI_NextVersion -ConfigFile $ConfigFile
    Write-Host "Initial version: $version"
    return $version
}

function GITHUB_NextVersion {
    param (
        [string]$ConfigFile = ".\setup.cfg",
        [string]$PyVersionFile = ".\${ProjectName}\__init__.py"
    )


    # Extract the version, increment it, and prepare the updated version string
    $version = "$(git tag -l --format='VERSION=%(refname:short)' | Sort-Object -Descending | Select-Object -First 1)" -split "=v", 2 | ForEach-Object { $_.Trim() } | Select-Object -Last 1

    if ($version -And $TagName -eq "0.0.0") {
        $newVersion = _NextVersionString -Version $version
        Write-Host "Next version (git): $newVersion"
        return $newVersion
    } else {
        if ($TagName -ne "0.0.0") {
            # $TagName = $version
            # $TagName = _NextVersionString -Version $TagName
            Write-Host "Next version (tag): $TagName"
            return $TagName
        }
        $newVersion = InitRepo -ConfigFile $ConfigFile
        Write-Host "Next version (init): $newVersion"
        return $newVersion
    }
}

Function GITHUB_UpdateVersion {
    param (
        [string]$ConfigFile = ".\setup.cfg",
        [string]$PyVersionFile = ".\${ProjectName}\__init__.py"
    )

    $newVersion = GITHUB_NextVersion -ConfigFile $ConfigFile

    Write-Host "Updating version to $newVersion"

    # First update the init file so that in case something goes wrong 
    # the version doesn't persist in the config file
    if (Test-Path $PyVersionFile) {
        $initContent = Get-Content -Path $PyVersionFile
        $initContent = $initContent -replace "__version__\s*=\s*.+", "__version__ = '$newVersion'"
        Set-Content -Path $PyVersionFile -Value $initContent
    }

    # Read file content
    $fileContent = Get-Content -Path $ConfigFile

    if (Test-Path $ConfigFile) {
        # Update the version line in the file content
        $updatedContent = $fileContent -replace "version\s*=\s*.+", "version = $newVersion"

        # Write the updated content back to the file
        Set-Content -Path $ConfigFile -Value $updatedContent
    }

    return $newVersion
}


Function _PYPI_DistName {
    param (
        [string]$Version,
        [string]$Append = ".tar.gz"
    )

    return "$ProjectName-$Version$Append"
}

Function PYPI_Build {
    py .\setup.py sdist
}

Function PYPI_Check {
    param (
        [string]$Version
    )

    $distFile = _PYPI_DistName -Version $Version
    py -m twine check "./dist/${distFile}"
}

Function PYPI_Upload {
    param (
        [string]$Version
    )

    $distFile = _PYPI_DistName -Version $Version
    python3 -m twine upload "./dist/${distFile}"
}

if ($Tag) {
    $version = GITHUB_UpdateVersion # Increment the package version  (setup.cfg)
    GITHUB_Upload -Version $version # Upload the package             (git push)
    PYPI_Build                      # Build the package              (python setup.py sdist)
    PYPI_Check -Version $version    # Check the package              (twine check dist/<LATEST>)
    PYPI_Upload -Version $version   # Upload the package             (twine upload dist/<LATEST>)
} else {
    GITHUB_Upload # Upload the package
}




