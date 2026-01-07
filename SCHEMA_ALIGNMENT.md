# Schema Alignment Fix

## Issue
The API schema and seed script were using fields that don't exist in the training dataset:
- `brand` - not in dataset
- `price` - should be `actual_price`
- `num_reviews` - should be `rating_count`
- `name` - should be `product_name` (in dataset)

## Changes Made

### 1. PredictionRequest Schema (`src/api/schemas/prediction.py`)
**Before:**
- `price` (should be `actual_price`)
- `num_reviews` (should be `rating_count`)
- `brand` (not in dataset)

**After:**
- `actual_price` ✅ (matches dataset)
- `category` ✅ (matches dataset)
- `rating` ✅ (matches dataset)
- `rating_count` ✅ (matches dataset)
- `product_name` ✅ (matches dataset)
- `about_product` ✅ (matches dataset)
- `discounted_price` ✅ (matches dataset)
- `img_link` ✅ (matches dataset)
- `product_link` ✅ (matches dataset)

### 2. Seed Script (`scripts/seed_database.py`)
**Before:**
- Used hardcoded sample products with made-up fields
- Included `brand` field not in dataset

**After:**
- Reads from actual dataset file: `data/raw/amazon_sales_dataset.csv`
- Maps dataset columns to Product model fields:
  - `product_name` → `name` (Product model field)
  - `actual_price` → `price` (Product model field)
  - `rating_count` → `num_reviews` (Product model field)
  - `about_product` → `description` (Product model field)
- Stores additional dataset fields in `attributes` JSON field
- Cleans currency symbols (₹) and formatting from prices

### 3. Guardrails Service (`src/services/guardrails_service.py`)
**Before:**
- Validated `price` field

**After:**
- Validates `actual_price` field (matches dataset)
- Validates `rating_count` instead of `num_reviews`
- Added validation for optional fields

## Dataset Columns (Actual)
1. `product_id`
2. `product_name`
3. `category`
4. `discounted_price`
5. `actual_price`
6. `discount_percentage` (target variable)
7. `rating`
8. `rating_count`
9. `about_product`
10. `user_id`
11. `user_name`
12. `review_id`
13. `review_title`
14. `review_content`
15. `img_link`
16. `product_link`

## Product Model Fields (Database)
- `id` (UUID)
- `name` (maps from `product_name`)
- `category`
- `brand` (optional, not in dataset)
- `price` (maps from `actual_price`)
- `discount_percentage`
- `rating`
- `num_reviews` (maps from `rating_count`)
- `description` (maps from `about_product`)
- `attributes` (JSON - stores additional dataset fields)

## API Request Example
```json
{
  "actual_price": 1099.0,
  "category": "Electronics",
  "rating": 4.2,
  "rating_count": 24269,
  "product_name": "Wireless Headphones",
  "about_product": "High-quality wireless headphones..."
}
```

## Notes
- The Product database model uses different field names than the dataset (for backward compatibility)
- The seed script maps dataset fields to model fields
- The API accepts dataset field names directly
- The predictor handles the mapping internally via feature engineering



