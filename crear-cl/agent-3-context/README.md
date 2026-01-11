# Agent 3 PDF Reference Context

This folder should contain PDF documents that provide reference material for PAES question generation.

## Required PDFs

Place your 4 PDF files here:

1. **guideline.pdf** (or similar name)
   - Guidelines for PAES question design
   - DEMRE standards and criteria

2. **example1.pdf**, **example2.pdf**, **example3.pdf** (or similar names)
   - Example texts with questions
   - Sample question formats
   - Reference implementations

## How It Works

- Agent 3 loads all PDFs from this folder at startup
- The content is extracted and included in every question generation prompt
- This ensures consistent PAES-style questions across all articles

## File Requirements

- Files must have `.pdf` extension
- PDFs should be text-based (not scanned images)
- Total size: recommend < 10MB for faster loading

## If No PDFs Are Present

The system will still work but will generate questions without the reference context. You'll see a warning message in the console.

