#!/usr/bin/env python3
"""Interactive chat with the deployed AgentCore agent."""

import argparse
import json
import os
import sys
import boto3

# Default runtime ARN - set AGENT_RUNTIME_ARN in .env after running deploy_to_agentcore.py
# The deploy script writes the new ARN to .env automatically under AGENT_RUNTIME_ARN.
DEFAULT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")

def chat(runtime_arn: str):
    client = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    print("=" * 60)
    print("x402 Payer Agent - Interactive Chat")
    print("=" * 60)
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            if not user_input:
                continue
                
            print("Agent: ", end="", flush=True)
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                payload=json.dumps({'message': user_input}).encode('utf-8'),
            )
            
            result = json.loads(response['response'].read())
            print(result.get('response', 'No response'))
            print()
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive chat with x402 Payer Agent")
    parser.add_argument(
        "--runtime-arn",
        default=DEFAULT_RUNTIME_ARN,
        help="AgentCore Runtime ARN (default: AGENT_RUNTIME_ARN env var, set by deploy_to_agentcore.py)"
    )
    args = parser.parse_args()
    if not args.runtime_arn:
        print("Error: AGENT_RUNTIME_ARN not set. Run deploy_to_agentcore.py first, or pass --runtime-arn.")
        sys.exit(1)
    chat(args.runtime_arn)
