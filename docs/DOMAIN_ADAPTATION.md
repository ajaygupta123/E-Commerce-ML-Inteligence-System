# Domain Adaptation Implementation

## Overview

This document describes the domain-specific adaptation techniques implemented to enhance LLM accuracy, tone alignment, and domain understanding for the e-commerce RAG system.

## Implementation Date
2026-01-04

## Techniques Implemented

### 1. Enhanced System Prompt with Few-Shot Examples

**Location**: [`src/services/rag_service.py`](src/services/rag_service.py) - `SYSTEM_PROMPT`

**Features**:
- **Tone & Style Guidelines**: Professional yet friendly, concise, factual, clear formatting
- **Domain Terminology**: Standard e-commerce terms, price formatting (₹ or $), rating format (X.X/5.0 stars)
- **Few-Shot Examples**: Four complete examples showing desired response formats for:
  - Comparison questions
  - Price questions
  - Feature questions
  - Category questions

**Impact**: Provides clear guidance to the LLM on how to structure responses, ensuring consistency and domain-appropriate language.

### 2. Question Type Classification

**Location**: [`src/utils/helpers.py`](src/utils/helpers.py) - `classify_question_type()`

**Question Types**:
- `COMPARISON`: Questions asking to compare products (e.g., "compare", "difference", "better", "vs")
- `PRICE`: Questions about pricing (e.g., "price", "cheap", "expensive", "affordable")
- `FEATURE`: Questions about product features (e.g., "feature", "specification", "support", "compatible")
- `CATEGORY`: Questions about product categories (e.g., "category", "available", "what products")
- `GENERAL`: Default for other questions

**Implementation**: Pattern-based classification using regex matching on question text.

**Impact**: Enables question-type-specific handling for better response formatting and context building.

### 3. Response Template System

**Location**: [`src/services/rag_service.py`](src/services/rag_service.py) - `_get_response_template()`

**Templates**:
- **Comparison**: Structured comparison with key differences and recommendations
- **Price**: Price-focused with value propositions, sorted by price
- **Feature**: Feature lists with technical specifications
- **Category**: Grouped by category with clear headings
- **General**: Structured formatting with key information highlighted

**Impact**: Guides LLM to format responses appropriately for each question type, improving readability and usefulness.

### 4. Enhanced Context Building

**Location**: [`src/services/rag_service.py`](src/services/rag_service.py) - `_build_context()`

**Enhancements**:
- **Question-Type-Specific Formatting**: Context is formatted differently based on question type
- **Comparison Questions**: Emphasizes differences, includes full descriptions (300 chars)
- **Price Questions**: Sorts products by price, emphasizes price and value
- **Feature Questions**: Includes full descriptions (400 chars) for feature extraction
- **Category Questions**: Groups products by category for better organization
- **General Questions**: Balanced format with 250 char descriptions

**Impact**: Provides the most relevant information to the LLM based on what the user is asking, improving answer quality.

### 5. Improved Query Validation

**Location**: [`src/utils/helpers.py`](src/utils/helpers.py) - `validate_ecommerce_query()`

**Enhancements**:
- **Expanded Keywords**: 50+ e-commerce keywords including:
  - Product terms (product, item, goods, merchandise)
  - Price terms (price, cost, discount, sale, deal, affordable)
  - Shopping actions (buy, purchase, order, cart, shop)
  - Product attributes (category, rating, review, feature)
  - Comparison terms (compare, recommend, choose, option)
  - Common product categories (electronics, clothing, accessories, etc.)
  - Product types (cable, headphone, phone, laptop, etc.)
- **Pattern Matching**: Regex patterns for product-related question structures
- **Better Semantic Understanding**: More comprehensive coverage of e-commerce queries

**Impact**: Better detection of e-commerce-related queries, reducing false rejections.

### 6. Integration into RAG Pipeline

**Location**: [`src/services/rag_service.py`](src/services/rag_service.py) - `answer_question()`

**Flow**:
1. Query validation (enhanced)
2. Question type classification
3. Context building (question-type-specific)
4. Response template selection
5. LLM generation with enhanced prompt
6. Metadata includes question type

**Impact**: End-to-end domain adaptation throughout the RAG pipeline.

## Test Results

### Test 1: Comparison Question
- **Question**: "Compare the USB cables available"
- **Classification**: `comparison` ✓
- **Response**: Structured comparison with key differences, formatted clearly
- **Quality**: High - includes recommendations and clear formatting

### Test 2: Price Question
- **Question**: "What are the cheapest USB cables?"
- **Classification**: `price` ✓
- **Response**: Price-focused, sorted by price, includes value propositions
- **Quality**: High - emphasizes price and value

### Test 3: Feature Question
- **Question**: "Which cables support fast charging?"
- **Classification**: `feature` ✓
- **Response**: Feature-focused with technical specifications
- **Quality**: High - detailed feature information

### Test 4: Category Question
- **Question**: "What electronics products are available?"
- **Classification**: `category` ✓
- **Response**: Grouped by category with clear headings
- **Quality**: High - well-organized by category

## Metrics

- **Question Type Classification Accuracy**: 100% (all test cases correctly classified)
- **Response Formatting**: Consistent across question types
- **Domain Terminology**: Proper use of e-commerce terms (₹, /5.0 stars, categories)
- **Tone**: Professional yet friendly, concise, factual

## Comparison: Before vs. After

### Before
- Basic system prompt with minimal guidelines
- No question type awareness
- Fixed context formatting
- Simple keyword-based validation
- Generic responses

### After
- Comprehensive system prompt with few-shot examples
- Question type classification and specific handling
- Dynamic context formatting based on question type
- Enhanced validation with 50+ keywords and patterns
- Question-type-specific response templates
- Domain-appropriate terminology and formatting

## Files Modified

1. **`src/services/rag_service.py`**
   - Enhanced `SYSTEM_PROMPT` with few-shot examples and tone guidelines
   - Added `_get_response_template()` method
   - Enhanced `_build_context()` with question-type-specific formatting
   - Integrated question classification into `answer_question()`

2. **`src/utils/helpers.py`**
   - Added `QuestionType` enum
   - Added `classify_question_type()` function
   - Enhanced `validate_ecommerce_query()` with comprehensive keywords

## Future Enhancements

Potential improvements for production:
1. **ML-based Question Classification**: Replace pattern matching with a trained classifier
2. **Dynamic Few-Shot Selection**: Select few-shot examples based on question type
3. **Response Quality Scoring**: Add LLM-as-judge to score response quality
4. **A/B Testing**: Test different prompt variations
5. **User Feedback Loop**: Incorporate user feedback to improve prompts
6. **Multi-language Support**: Extend to support multiple languages

## References

- Architecture Decision: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - Section 3: LLM Strategy
- Implementation: [`src/services/rag_service.py`](src/services/rag_service.py)
- Utilities: [`src/utils/helpers.py`](src/utils/helpers.py)


