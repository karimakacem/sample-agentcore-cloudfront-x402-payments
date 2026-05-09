# Quick Start

Get the x402 payment demo running in under 30 minutes.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Node.js | 18+ | `node --version` |
| Python | 3.10+ | `python3 --version` |
| AWS CLI | 2.x | `aws --version` |
| AWS CDK | 2.x | `cdk --version` |
| Docker | 20+ | `docker --version` |

Also required:
- AWS account with Bedrock AgentCore access
- AgentCore Payments setup completed (see `agentcore-payments-beta/quickstart/`)
- [Coinbase Developer Platform](https://portal.cdp.coinbase.com/) API keys (for AgentCore Payments credential provider setup)

## Full Deployment

### Step 1: Clone (2 min)

```bash
git clone https://github.com/aws-samples/sample-agentcore-cloudfront-x402-payments
cd sample-agentcore-cloudfront-x402-payments
./scripts/setup.sh
```

### Step 2: Configure Credentials (5 min)

**AWS:**
```bash
aws configure
aws sts get-caller-identity
```

**Seller:**

Edit `seller-infrastructure/.env` with your wallet address:
```bash
PAYMENT_RECIPIENT_ADDRESS=<YOUR_SELLER_WALLET_ADDRESS>
```

### Step 3: Deploy Seller (10 min)

```bash
cd seller-infrastructure
npm install
npx cdk bootstrap  # first time only
npx cdk deploy
```

### Step 4: Set Up AgentCore Payments (10 min)

This creates the payment infrastructure (credential provider, manager, connector):

```bash
cd agentcore-payments-beta/quickstart
cp .env.sample .env
# Fill in: COINBASE_API_KEY_ID, COINBASE_API_KEY_SECRET, COINBASE_WALLET_SECRET

bash setup_roles.sh       # Creates 4 IAM roles
bash setup_model.sh       # Installs boto3 service models (needed until GA)
bash setup_manager.sh     # Creates credential provider, manager, connector
```

Save the output values — you'll need `MANAGER_ARN` and `CONNECTOR_ID`.

Then create an instrument and session:

```bash
cd ../scripts
cp .env.sample .env
# Fill in: MANAGER_ARN, CONNECTOR_ID, role ARNs from setup_roles.sh output
bash e2e-test.sh
```

Save `PAYMENT_INSTRUMENT_ID` and `PAYMENT_SESSION_ID` from the output.

Fund the wallet with testnet USDC at https://faucet.circle.com/ (Base Sepolia).

### Step 5: Configure Payer Agent

```bash
cd payer-agent
cp .env.example .env
```

Fill in the `.env` file:
```bash
MANAGER_ARN=<from step 4>
PAYMENT_SESSION_ID=<from step 4>
PAYMENT_INSTRUMENT_ID=<from step 4>
PROCESS_PAYMENT_ROLE_ARN=<from setup_roles.sh output>
USER_ID=test-user-12345
SELLER_API_URL=<CloudFront URL from step 3>
```

### Step 6: Deploy Payer Infrastructure (10 min)

```bash
cd payer-infrastructure
npm install
npx cdk bootstrap  # first time only
npx cdk deploy --all
```

### Step 7: Deploy Agent

```bash
cd payer-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/deploy_to_agentcore.py
```

### Step 8: Test

```bash
cd payer-agent
source .venv/bin/activate

# Test MCP tool discovery
python scripts/test_gateway_target.py

# Invoke agent
python scripts/invoke_gateway.py "Get me the premium article"

# Run tests
pytest tests/ -v
```

### Step 9: Web UI (Optional)

Start the backend API server and frontend in separate terminals:
```bash
# Terminal 1: Backend
cd payer-agent
source .venv/bin/activate
python -m agent.api_server

# Terminal 2: Frontend
cd web-ui
npm install
npm run dev
```

## MCP Tools

| Tool | Price (USDC) |
|------|--------------|
| `get_premium_article` | 0.001 |
| `get_weather_data` | 0.0005 |
| `get_market_analysis` | 0.002 |
| `get_research_report` | 0.005 |
| `get_dataset` | 0.01 |
| `get_tutorial` | 0.003 |

## Troubleshooting

**Module not found:**
```bash
cd payer-agent && source .venv/bin/activate && pip install -e ".[dev]"
```

**AWS credentials:**
```bash
aws configure
```

**CDK bootstrap:**
```bash
npx cdk bootstrap aws://ACCOUNT_ID/REGION
```

**ProcessPayment fails with "Budget exceeded":**
Create a new session with a higher `maxSpendAmount` using the management role.

**ProcessPayment fails with "Insufficient funds":**
Fund the wallet with USDC at https://faucet.circle.com/ (select Base Sepolia network).

**Lambda@Edge region:**
Lambda@Edge requires `us-east-1`. This is hardcoded in the CDK stack — no configuration needed.

## References

- [README.md](README.md) - Full architecture
- [agentcore-payments-beta/docs/getting-started.md](agentcore-payments-beta/docs/getting-started.md) - AgentCore Payments guide
- [x402 Protocol](https://github.com/coinbase/x402/tree/main/specs)
