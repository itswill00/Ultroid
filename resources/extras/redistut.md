# Redis Database Provisioning Guide

Follow these steps to initialize a managed Redis instance for Ultroid.

### 1. Account Initialization
- Navigate to [Redis.com](https://redis.com) and select the **Try Free** option.
- Complete the registration process with valid credentials.
- Verify your account through the confirmation link sent to your email.

### 2. Subscription Deployment
- Log in to the Cloud Console.
- Deploy a new subscription under the **Fixed Size** tier (choose the free plan).
- Assign a unique name to your subscription.

### 3. Database Activation
- Create a new database instance within your subscription.
- Wait approximately 5 minutes for the environment to provision.

### 4. Credential Extraction
- Locate the **Endpoint** URL and the **Access Control & Security** section.
- Map these credentials to your `.env` file:
    - `Endpoint URL` → `REDIS_URI`
    - `Security Password` → `REDIS_PASSWORD`

---
<p align="center">
  <i>Ensure your credentials remain private. Never share your .env file.</i>
</p>
