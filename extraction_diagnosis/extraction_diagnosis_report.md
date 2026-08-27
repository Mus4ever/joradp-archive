# PDF Extraction Problem Diagnosis Report

## Executive Summary

**Status**: EXTRACTION PROBLEMS CONFIRMED

**Findings**: Multiple PDFs show duplicated fragments, broken characters, and incorrect block ordering in PyMuPDF extraction.

**Recommendation**: STOP MASS EXTRACTION - Implement coordinate-based block ordering before proceeding.

## Test Configuration

**PDFs Tested**: 10 Arabic PDFs
- AR 2007-3, AR 2007-16, AR 2007-34, AR 2018-72, AR 2012-1
- AR 2001-37, AR 2002-6, AR 2003-41, AR 2011-19, AR 2007-19

**Page Tested**: Page 5 (content page)

**Extraction Methods Tested**:
1. `page.get_text()` - Default method
2. `page.get_text("blocks")` - Block-based extraction
3. `page.get_text("words")` - Word-based extraction
4. `page.get_text("dict")` - Dictionary extraction (FAILED for all)
5. `page.get_text(sort=True)` - Sorted extraction

## Key Findings

### 1. Text Duplication Confirmed

**Example: AR 2007-19 (Page 5)**
```
اﺗﻔﺎﻗﻴﺔ اﻧﺸﺎء
اﺗﻔﺎﻗﻴﺔ اﻧﺸﺎء  ← DUPLICATE
ﺠﻨﺔ اﻹﺳﻼﻣﻴﺔ ﻟﻠﻬﻼل اﻟﺪوﻟﻲ
ﺠﻨﺔ اﻹﺳﻼﻣﻴﺔ ﻟﻠﻬﻼل اﻟﺪوﻟﻲّاﻟﻠ اﻟﻠ  ← DUPLICATE WITH FRAGMENT
```

**Observation**: Lines appear multiple times with slight variations, indicating block reordering issues.

### 2. Low Similarity Between Methods

**Text Similarity (default vs sorted)**:
- AR 2007-3: 12.49%
- AR 2007-16: 10.80%
- AR 2007-34: 12.78%
- AR 2018-72: 4.18%
- AR 2012-1: 11.89%
- AR 2003-41: 35.17%
- AR 2011-19: 10.29%
- AR 2007-19: 10.98%

**Interpretation**: Very low similarity (4-12%) indicates significant reordering between methods. This suggests PyMuPDF's default ordering is incorrect for RTL documents.

### 3. Scanned PDFs Identified

**SCANNED PDFs (0 chars)**:
- AR 2001-37: 0 chars (needs OCR)
- AR 2002-6: 0 chars (needs OCR)

**Classification**: These are image-only PDFs without native text extraction capability.

### 4. Mixed-Language Content

**High Latin Content**:
- AR 2003-41: 1068 Latin chars, 0 Arabic chars (bilingual/French page)
- Other PDFs: 5-8% Latin content (normal for technical/legal documents)

**Interpretation**: Mixed-language content is legitimate and expected in official documents.

### 5. Dictionary Method Failure

**Status**: `page.get_text("dict")` FAILED for all 10 PDFs

**Error**: KeyError: 'text'

**Impact**: Cannot access detailed block structure information through dict method.

## Root Cause Analysis

### Primary Issue: Incorrect Block Ordering

**Evidence**:
1. Very low similarity between default and sorted extraction (4-12%)
2. Text duplication patterns in extracted output
3. Fragmented text with markers like "p" appearing mid-sentence

**Hypothesis**: PyMuPDF's default block ordering does not account for RTL column structure. In Arabic documents with multiple columns, blocks may be extracted in left-to-right order instead of right-to-left, causing:
- Wrong column order
- Duplicate text fragments
- Fragmented sentences

### Secondary Issue: Character Mapping

**Evidence**: Some characters appear broken or duplicated in the extracted text.

**Hypothesis**: Font/ToUnicode mapping issues in certain PDFs, but this is less severe than the ordering problem.

## Recommended Strategy

### 1. Implement Coordinate-Based Block Ordering

**Algorithm**:
1. Extract blocks with coordinates (x0, y0, x1, y1)
2. Sort blocks by Y coordinate (top-to-bottom)
3. For blocks with similar Y coordinates (same line):
   - Sort by X coordinate in RTL order (right-to-left for Arabic)
   - Detect column boundaries based on X coordinate gaps
   - Order columns right-to-left

### 2. Classification Strategy

**For each page**:
1. Check native text availability (>0 chars)
2. If 0 chars: classify as NEEDS_OCR
3. If >0 chars: use coordinate-based block ordering
4. Apply RTL-aware column ordering for Arabic documents

### 3. Diagnostic Extraction Method

**Recommended method**:
```python
# Use blocks with coordinate-based RTL ordering
blocks = page.get_text("blocks")
# Filter text blocks (type 0)
text_blocks = [b for b in blocks if b[6] == 0]
# Sort by Y (top-to-bottom)
text_blocks.sort(key=lambda b: b[1])
# For same Y, sort by X in RTL order
# Implement column detection and RTL column ordering
```

## Testing Required

### 1. Prototype RTL Block Ordering

**Test**: Implement coordinate-based RTL block ordering on the 10 problematic PDFs

**Success Criteria**:
- Text similarity > 80% vs manual inspection
- No duplicate fragments
- Logical reading order preserved

### 2. Alternative Extraction Method

**Test**: Compare with pdftotext or pdfplumber as diagnostic

**Purpose**: Validate whether the problem is PyMuPDF-specific or general

### 3. Scanned PDF Detection

**Test**: Improve OCR threshold calibration for better scanned/native classification

## Current Limitations

1. **Manual Inspection Required**: Text files vs rendered pages need manual comparison
2. **Sample Size**: Only 10 PDFs tested (need broader validation)
3. **Dict Method Unavailable**: Cannot access detailed block structure due to method failure
4. **Prototype Not Implemented**: Coordinate-based RTL ordering needs development

## Conclusion

**CRITICAL FINDING**: The PyMuPDF default extraction method produces unusable text for Arabic PDFs due to incorrect block ordering.

**IMMEDIATE ACTION REQUIRED**:
1. Implement coordinate-based RTL block ordering
2. Test on problematic PDFs
3. Validate against rendered pages
4. Only proceed with mass extraction after validation

**MASS EXTRACTION**: NOT AUTHORIZED until extraction problems are resolved.

## Files Generated

- `extraction_diagnosis/diagnosis_results.json` - Raw extraction results
- `extraction_diagnosis/analysis_report.txt` - Automated analysis
- `extraction_diagnosis/*_page5_*.txt` - Individual method outputs
- `extraction_diagnosis/*_page5.png` - Rendered pages for comparison
- `extraction_diagnosis/extraction_diagnosis_report.md` - This report

## Next Steps

1. **Implement** coordinate-based RTL block ordering prototype
2. **Test** on 10 problematic PDFs
3. **Validate** against rendered pages
4. **Document** results and methodology
5. **Approve** before mass extraction

**Date**: 2026-08-27