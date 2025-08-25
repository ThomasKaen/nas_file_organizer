# run.ps1
# Build and run the NAS Organizer container with proper mounts

# Change these if your Inbox/Archive are somewhere else
$Inbox    = "C:\Users\Tamas\Documents\Inbox"
$Archive  = "C:\Users\Tamas\Documents\Archive"

# Current project dir (where rules.yaml + logs live)
$Project  = $PSScriptRoot

# Image name
$Image = "nas-organizer"

Write-Host "Building Docker image $Image..."
docker build -t $Image $Project

Write-Host "Running Docker container..."
docker run --rm `
  -v "$Project\rules.yaml:/app/rules.yaml" `
  -v "$Inbox:/data/inbox" `
  -v "$Archive:/data/archive" `
  -v "$Project\logs:/app/logs" `
  $Image