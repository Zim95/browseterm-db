# browseterm-db
Database Setup for Browseterm

# Entities
1. **User** - The user of the application - Authenticated via Google or GitHub OAuth  
2. **Container** - Docker containers that users create and manage  
3. **Subscription** - User subscription data and status  
4. **SubscriptionType** - Subscription plan definitions with pricing and limits  
5. **Orders** - Payment records for subscription purchases and renewals  

# Relationships:
1. User - Container: 1 to Many (One user can have multiple containers)  
2. User - Subscription: 1 to 1 (Each user has one active subscription)  
3. User - Orders: 1 to Many (Users can have multiple payment records)  
4. Subscription - SubscriptionType: Many to 1 (Multiple subscriptions can use same type)  
5. Subscription - Orders: 1 to Many (One subscription can have multiple payments/renewals)  
6. SubscriptionType - Orders: 1 to Many (One plan type can have multiple orders)  

**Note**: Subscription history is maintained via CDC (Change Data Capture) for audit purposes.


# Database Design

## 1. User
```sql
- id: string - UUID (PK)
- email: string - Email (unique, indexed)
- provider: enum - Authentication provider (google, github)
- provider_id: string - ID from OAuth provider
- created_at: datetime - Account creation timestamp
- updated_at: datetime - Last modification timestamp
- last_login: datetime - Last login timestamp (nullable)
- is_active: boolean - Account status (default: true)
```

## 2. Container
```sql
- id: string - UUID (PK)
- user_id: string - FK to User
- name: string - User-defined container name
- image: string - Docker image used
- status: enum - Container status (Running, Stopped, Failed, Deleted)
- cpu_limit: string - CPU allocation (e.g., "1.0")
- memory_limit: string - Memory allocation (e.g., "1GB")
- port_mappings: json - Port configuration
- environment_vars: json - Environment variables
- created_at: datetime - Container creation timestamp
- updated_at: datetime - Last modification timestamp
- deleted_at: datetime - Soft delete timestamp (nullable)
```

## 3. Subscription
```sql
- id: string - UUID (PK)
- user_id: string - FK to User (unique for 1-to-1 relationship)
- subscription_type_id: string - FK to SubscriptionType
- status: enum - Subscription status (Active, Expired, Cancelled, Pending)
- created_at: datetime - Subscription start date
- updated_at: datetime - Last modification timestamp
- valid_until: datetime - Subscription expiry date
- auto_renew: boolean - Auto-renewal setting (default: true)
- cancelled_at: datetime - Cancellation timestamp (nullable)
```
**Foreign Key Constraints:**
- user_id: ON DELETE CASCADE (if user deleted, remove subscription)
- subscription_type_id: ON DELETE RESTRICT (prevent deletion of active subscription types)

## 4. SubscriptionType
```sql
- id: string - UUID (PK)
- name: string - Display name (e.g., "Pro Plan", "Enterprise")
- type: string - Internal type identifier
- amount: decimal - Price (use decimal for currency precision)
- currency: string - Currency code (USD, EUR, etc.)
- duration_days: integer - Subscription duration in days
- max_containers: integer - Maximum containers allowed
- cpu_limit_per_container: string - CPU limit per container
- memory_limit_per_container: string - Memory limit per container
- description: text - Plan description and features
- is_active: boolean - Whether new subscriptions are allowed
- created_at: datetime - Plan creation timestamp
- updated_at: datetime - Last modification timestamp
```

## 5. Orders
```sql
- id: string - UUID (PK)
- user_id: string - FK to User
- subscription_id: string - FK to Subscription (nullable for first-time orders)
- subscription_type_id: string - FK to SubscriptionType
- amount: decimal - Amount paid
- currency: string - Currency used for payment
- status: enum - Payment status (Pending, Paid, Failed, Refunded)
- payment_method: string - Payment provider (stripe, paypal, etc.)
- payment_provider_id: string - External payment reference ID
- created_at: datetime - Order creation timestamp
- updated_at: datetime - Last modification timestamp
- paid_at: datetime - Payment completion timestamp (nullable)
```
**Foreign Key Constraints:**
- user_id: ON DELETE RESTRICT (preserve order history)
- subscription_id: ON DELETE SET NULL (keep order if subscription deleted)
- subscription_type_id: ON DELETE RESTRICT (preserve historical pricing)

# Database Indexes

## Essential Indexes for Performance
```sql
-- User table indexes
CREATE UNIQUE INDEX idx_user_email ON User(email);
CREATE INDEX idx_user_provider ON User(provider);
CREATE INDEX idx_user_is_active ON User(is_active);

-- Container table indexes
CREATE INDEX idx_container_user_id ON Container(user_id);
CREATE INDEX idx_container_status ON Container(status);
CREATE INDEX idx_container_user_status ON Container(user_id, status);

-- Subscription table indexes
CREATE UNIQUE INDEX idx_subscription_user_id ON Subscription(user_id);
CREATE INDEX idx_subscription_status ON Subscription(status);
CREATE INDEX idx_subscription_type_id ON Subscription(subscription_type_id);
CREATE INDEX idx_subscription_valid_until ON Subscription(valid_until);

-- SubscriptionType table indexes
CREATE INDEX idx_subscription_type_is_active ON SubscriptionType(is_active);
CREATE INDEX idx_subscription_type_amount ON SubscriptionType(amount);

-- Orders table indexes
CREATE INDEX idx_orders_user_id ON Orders(user_id);
CREATE INDEX idx_orders_subscription_id ON Orders(subscription_id);
CREATE INDEX idx_orders_status ON Orders(status);
CREATE INDEX idx_orders_created_at ON Orders(created_at);
CREATE INDEX idx_orders_user_status ON Orders(user_id, status);
```

# Business Logic Considerations

## Subscription Management
1. **Subscription Lifecycle**
   - New users start with a trial or basic plan  
   - Upgrades/downgrades take effect immediately with proration  
   - Cancellations remain active until the current period ends  
   - Expired subscriptions move containers to "stopped" state  

2. **Container Limits Enforcement**
   - Check `max_containers` from `SubscriptionType` before allowing new containers  
   - Enforce CPU/memory limits based on subscription plan  
   - Handle limit reductions when downgrading plans  

3. **Payment Processing**
   - Failed payments trigger retry logic (3 attempts over 7 days)  
   - Grace period of 7 days before subscription suspension  
   - Automatic subscription reactivation upon successful payment  

## Data Integrity Rules
1. **User Deletion**: Soft delete recommended for GDPR compliance  
2. **Container Cleanup**: Implement background job to clean up deleted containers  
3. **Subscription History**: Maintain audit trail via CDC for billing disputes  
4. **Order Records**: Never delete order records for financial auditing  

## Security Considerations
1. **Access Control**: Users can only access their own containers and subscription data  
2. **API Rate Limiting**: Implement rate limits on container operations  
3. **Data Encryption**: Encrypt sensitive fields like payment provider IDs  
4. **Audit Logging**: Log all critical operations (container create/delete, subscription changes)  

## Implementation Notes
1. **Database Choice**: PostgreSQL recommended for JSON field support and ACID compliance  
2. **Migrations**: Use versioned database migrations for schema changes  
3. **Backup Strategy**: Daily encrypted backups with point-in-time recovery  
4. **Monitoring**: Set up alerts for failed payments, subscription expirations, and high container usage  
