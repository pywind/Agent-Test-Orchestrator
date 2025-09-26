# Web Checkout Stories

- As a shopper, I must sign in with email and password to access my cart: Verify login form with validation.
- As a shopper, I must add items to the cart from the catalog listing: Ensure add-to-cart updates totals.
- As a shopper, I must remove an item from the cart before checkout: Confirm cart count reflects removal.
- As a shopper, I must apply a promotion code: Validate discount is displayed and total updates.
- As a shopper, I must complete checkout with credit card: Confirm success page and order summary.

# API Contract
- Service must expose POST /api/cart to create a cart session: Response contains cartId.
- Service must expose POST /api/checkout to finalize purchase: Response returns receiptId.
