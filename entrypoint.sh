#!/bin/bash
set -e

# Exit on error
set -o errexit
set -o nounset
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check required environment variables
if [ -z "${S3_BUCKET:-}" ]; then
    print_error "S3_BUCKET environment variable is not set"
    exit 1
fi

# Set default values
S3_DATA_PREFIX="${S3_DATA_PREFIX:-data/}"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

print_message "Starting container initialization..."
print_message "S3 Bucket: ${S3_BUCKET}"
print_message "S3 Data Prefix: ${S3_DATA_PREFIX}"
print_message "AWS Region: ${AWS_REGION}"

# Ensure data directory exists
mkdir -p /app/data

# Required data files
DATA_FILES=(
    "postings_list.json"
    "all_topics_wikipedia_data.json"
    "doc_id_to_url.json"
)

# Download data files from S3
print_message "Downloading data files from S3..."
for file in "${DATA_FILES[@]}"; do
    s3_path="s3://${S3_BUCKET}/${S3_DATA_PREFIX}${file}"
    local_path="/app/data/${file}"
    
    print_message "Downloading ${file} from ${s3_path}..."
    
    # Attempt to download with retries
    max_retries=3
    retry_count=0
    download_success=false
    
    while [ $retry_count -lt $max_retries ]; do
        if aws s3 cp "${s3_path}" "${local_path}" --region "${AWS_REGION}" 2>/dev/null; then
            if [ -f "${local_path}" ] && [ -s "${local_path}" ]; then
                file_size=$(wc -c < "${local_path}" 2>/dev/null || echo "unknown")
                print_message "Successfully downloaded ${file} (${file_size} bytes)"
                download_success=true
                break
            else
                print_warning "Downloaded file ${file} is empty or doesn't exist, retrying..."
            fi
        else
            print_warning "Failed to download ${file}, attempt $((retry_count + 1))/${max_retries}"
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            sleep 2
        fi
    done
    
    if [ "$download_success" = false ]; then
        print_error "Failed to download ${file} after ${max_retries} attempts"
        print_error "Please ensure the file exists at ${s3_path} and the container has S3 read permissions"
        exit 1
    fi
done

# Verify all files exist and are not empty
print_message "Verifying downloaded data files..."
for file in "${DATA_FILES[@]}"; do
    local_path="/app/data/${file}"
    if [ ! -f "${local_path}" ]; then
        print_error "Required data file ${file} is missing"
        exit 1
    fi
    
    if [ ! -s "${local_path}" ]; then
        print_error "Required data file ${file} is empty"
        exit 1
    fi
    
    # Basic JSON validation
    if ! python3 -m json.tool "${local_path}" > /dev/null 2>&1; then
        print_error "Data file ${file} is not valid JSON"
        exit 1
    fi
done

print_message "All data files downloaded and verified successfully!"

# Download NLTK data if not already present
print_message "Downloading NLTK stopwords (if needed)..."
python3 -m nltk.downloader stopwords --quiet || print_warning "NLTK download failed, but continuing..."

# Print Python version for debugging
print_message "Python version: $(python3 --version)"

# Start the FastAPI application
print_message "Starting FastAPI application on port 8000..."
exec uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1

