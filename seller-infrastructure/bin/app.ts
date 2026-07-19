#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SellerStack } from '../lib/seller-stack';

const app = new cdk.App();

new SellerStack(app, 'X402SellerStack', {
  env: { region: 'us-east-1' }, // WAF for CloudFront must be us-east-1
  description: 'x402 Workshop: S3 + CloudFront + WAF AI Traffic Monetization',
});

app.synth();
