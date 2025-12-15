# Refunds and Discounts Feature Documentation

## Overview

This document describes the new refund and discount functionality added to the MobiPark application. The implementation includes:

1. **Refund Management**: Admin-only functionality to process refunds for existing payments
2. **Discount Codes**: Admin-managed discount codes that can be applied to payments
3. **Enhanced Payment Processing**: Support for applying discount codes during payment creation

## New Endpoints

### Refund Endpoints

#### 1. Create Refund (Admin Only)
- **POST** `/refunds`
- **Description**: Create a new refund for an existing payment
- **Authorization**: Admin only
- **Request Body**:
```json
{
  "original_transaction_id": "string",
  "amount": 50.0,
  "reason": "Customer requested refund"
}
```

#### 2. Get All Refunds
- **GET** `/refunds`
- **Description**: Get all refunds (admins see all, users see only their own)
- **Authorization**: Required (users see only refunds for their payments)

#### 3. Get Refund by ID
- **GET** `/refunds/{refund_id}`
- **Description**: Get a specific refund by ID
- **Authorization**: Required (users can only access refunds for their payments)

#### 4. Get Refunds for Transaction
- **GET** `/refunds/transaction/{transaction_id}`
- **Description**: Get all refunds for a specific payment transaction
- **Authorization**: Required (users can only access refunds for their payments)

### Discount Code Endpoints

#### 1. Create Discount Code (Admin Only)
- **POST** `/discount-codes`
- **Description**: Create a new discount code
- **Authorization**: Admin only
- **Request Body**:
```json
{
  "code": "SAVE10",
  "discount_type": "percentage",
  "discount_value": 10.0,
  "max_uses": 100,
  "expires_at": "2024-12-31T23:59:59"
}
```

#### 2. Get All Discount Codes (Admin Only)
- **GET** `/discount-codes`
- **Description**: Get all discount codes
- **Authorization**: Admin only

#### 3. Get Discount Code by Code (Admin Only)
- **GET** `/discount-codes/{code}`
- **Description**: Get a specific discount code
- **Authorization**: Admin only

#### 4. Update Discount Code (Admin Only)
- **PUT** `/discount-codes/{code}`
- **Description**: Update an existing discount code
- **Authorization**: Admin only

#### 5. Deactivate Discount Code (Admin Only)
- **DELETE** `/discount-codes/{code}`
- **Description**: Deactivate a discount code
- **Authorization**: Admin only

### Enhanced Payment Endpoint

#### Updated Payment Creation
- **POST** `/payments`
- **Description**: Create a payment with optional discount code
- **New Field**: `discount_code` (optional string)
- **Request Body**:
```json
{
  "amount": 100.0,
  "session_id": 1,
  "parking_lot_id": 1,
  "t_data": {
    "amount": 100.0,
    "date": "2024-12-06",
    "method": "credit_card",
    "issuer": "visa",
    "bank": "test_bank"
  },
  "discount_code": "SAVE10"
}
```

## Data Models

### Refund Model
```json
{
  "refund_id": "uuid-string",
  "original_transaction_id": "original-payment-id",
  "amount": 50.0,
  "reason": "Customer requested refund",
  "processed_by": "admin_username",
  "created_at": "06-12-2024 18:30:001733508600",
  "status": "completed",
  "refund_hash": "unique-hash"
}
```

### Discount Code Model
```json
{
  "code": "SAVE10",
  "discount_type": "percentage",
  "discount_value": 10.0,
  "max_uses": 100,
  "current_uses": 5,
  "active": true,
  "created_at": "06-12-2024 18:30:001733508600",
  "expires_at": "2024-12-31T23:59:59"
}
```

### Enhanced Payment Model
The payment model now includes:
- `original_amount`: Amount before discount (if discount applied)
- `discount_applied`: Discount code used (if any)
- `discount_amount`: Amount discounted (if any)

## Business Logic

### Discount Application
1. **Validation**: Discount code must exist, be active, not expired, and within usage limits
2. **Types**:
   - **Percentage**: Reduces payment by percentage (e.g., 10% off)
   - **Fixed**: Reduces payment by fixed amount (e.g., $5 off)
3. **Usage Tracking**: Automatically increments usage count when applied
4. **Limits**: Respects maximum usage limits and expiration dates

### Refund Processing
1. **Validation**: Original payment must exist and refund amount cannot exceed remaining refundable amount
2. **Tracking**: Multiple refunds per payment are supported
3. **Authorization**: Only admins can create refunds
4. **Audit Trail**: Tracks who processed the refund and when

## Security Features

### Authorization
- **Admin Only**: Refund creation, discount code management
- **User Access**: Users can only view refunds for their own payments
- **Authentication**: All endpoints require valid session tokens

### Validation
- **Amount Validation**: Refunds cannot exceed remaining refundable amount
- **Discount Validation**: Codes are validated for existence, activity, expiration, and usage limits
- **Input Sanitization**: All inputs are validated using Pydantic models

## Database Schema

### New Tables
1. **refunds**: Stores refund records
2. **discounts**: Stores discount codes (may already exist)

### Storage Functions Added
- `save_new_refund_to_db()`
- `get_refund_by_id()`
- `get_refunds_by_transaction_id()`
- `save_new_discount_to_db()`
- `get_discount_by_code()`
- `update_existing_discount_in_db()`

## Usage Examples

### 1. Create a Discount Code (Admin)
```bash
curl -X POST "http://localhost:12000/discount-codes" \
  -H "Authorization: admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "WELCOME20",
    "discount_type": "percentage",
    "discount_value": 20.0,
    "max_uses": 50,
    "expires_at": "2024-12-31T23:59:59"
  }'
```

### 2. Make Payment with Discount
```bash
curl -X POST "http://localhost:12000/payments" \
  -H "Authorization: user-token" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.0,
    "session_id": 1,
    "parking_lot_id": 1,
    "t_data": {
      "amount": 100.0,
      "date": "2024-12-06",
      "method": "credit_card",
      "issuer": "visa",
      "bank": "test_bank"
    },
    "discount_code": "WELCOME20"
  }'
```

### 3. Process a Refund (Admin)
```bash
curl -X POST "http://localhost:12000/refunds" \
  -H "Authorization: admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "original_transaction_id": "payment-transaction-id",
    "amount": 50.0,
    "reason": "Customer cancellation"
  }'
```

## Error Handling

### Common Error Responses
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions (non-admin trying admin operations)
- **404 Not Found**: Resource not found (payment, refund, discount code)
- **409 Conflict**: Discount code already exists
- **422 Unprocessable Entity**: Validation errors (invalid amounts, expired codes, etc.)

### Specific Validations
- Refund amount cannot exceed remaining refundable amount
- Discount codes must be active and not expired
- Discount codes cannot exceed usage limits
- Percentage discounts cannot exceed 100%

## Testing

A test script is provided (`test_refunds_discounts.py`) that verifies:
- Endpoint registration
- Authentication requirements
- Model schema updates
- Server health

## Future Enhancements

Potential improvements could include:
1. **Partial Refunds**: Support for multiple partial refunds
2. **Refund Approval Workflow**: Multi-step approval process
3. **Discount Analytics**: Usage statistics and reporting
4. **User-specific Discounts**: Personalized discount codes
5. **Automatic Discounts**: Rule-based discount application
6. **Refund Notifications**: Email/SMS notifications for refunds

## Migration Notes

### Existing Data
- Existing payments are compatible with the new schema
- New fields (`original_amount`, `discount_applied`, `discount_amount`) are optional
- No data migration required for existing payments

### Database Updates
- New tables (`refunds`, `discounts`) will be created automatically when first accessed
- Existing payment table structure remains unchanged