$ErrorActionPreference = "Stop"
Set-Location "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"

python -m pytest tests -v
python run_pipeline.py --step all --start 2023-01-01

$required = @(
  "data/features/factor_values.parquet",
  "data/features/feature_matrix.parquet",
  "data/features/factor_quality.parquet",
  "data/labels/labels.parquet",
  "data/predictions/predictions.parquet"
)

foreach ($path in $required) {
  if (-not (Test-Path $path)) {
    throw "Missing expected output: $path"
  }
}

Write-Host "Bias engine verification passed."
