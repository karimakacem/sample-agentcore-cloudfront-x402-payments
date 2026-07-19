import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as path from 'path';

const SELLER_WALLET = '0x7cc27d2b443D18eB556936142B31155eD07725De';

export class SellerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const contentBucket = new s3.Bucket(this, 'ContentBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // WAF WebACL — MonetizationConfig and Monetize action are new CloudFormation properties
    // injected via addPropertyOverride since CDK L1 types don't include them yet
    const webAcl = new wafv2.CfnWebACL(this, 'MonetizationWebAcl', {
      name: 'x402-workshop-monetization',
      scope: 'CLOUDFRONT',
      defaultAction: { allow: {} },
      description: 'Monetize AI agent access via x402',
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: 'x402Workshop',
        sampledRequestsEnabled: true,
      },
    });

    webAcl.addPropertyOverride('MonetizationConfig', {
      CurrencyMode: 'TEST',
      CryptoConfig: {
        PaymentNetworks: [{
          Chain: 'BASE_SEPOLIA',
          WalletAddress: SELLER_WALLET,
          Prices: [{ Amount: '0.001', Currency: 'USDC' }],
        }],
      },
    });

    webAcl.addPropertyOverride('Rules', [
      {
        Name: 'AllowCatalog',
        Priority: 0,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/catalog',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'EXACTLY',
          },
        },
        Action: { Allow: {} },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'Catalog',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'MonetizeDataset',
        Priority: 2,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/dataset',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'STARTS_WITH',
          },
        },
        Action: { Monetize: { PriceMultiplier: '10' } },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'Dataset',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'MonetizeResearchReport',
        Priority: 3,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/research-report',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'STARTS_WITH',
          },
        },
        Action: { Monetize: { PriceMultiplier: '5' } },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'ResearchReport',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'MonetizeTutorial',
        Priority: 4,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/tutorial',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'STARTS_WITH',
          },
        },
        Action: { Monetize: { PriceMultiplier: '3' } },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'Tutorial',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'MonetizeMarketAnalysis',
        Priority: 5,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/market-analysis',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'STARTS_WITH',
          },
        },
        Action: { Monetize: { PriceMultiplier: '2' } },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'MarketAnalysis',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'MonetizeAllApi',
        Priority: 6,
        Statement: {
          ByteMatchStatement: {
            SearchString: '/api/',
            FieldToMatch: { UriPath: {} },
            TextTransformations: [{ Priority: 0, Type: 'NONE' }],
            PositionalConstraint: 'STARTS_WITH',
          },
        },
        Action: { Monetize: {} },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AllApi',
          SampledRequestsEnabled: true,
        },
      },
    ]);

    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(contentBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
      },
      webAclId: webAcl.attrArn,
      comment: 'x402 Workshop Seller',
    });

    // Content files have no extension — S3 keys match /api/premium-article etc.
    new s3deploy.BucketDeployment(this, 'ContentDeployment', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../content'))],
      destinationBucket: contentBucket,
      contentType: 'application/json',
      distribution,
      distributionPaths: ['/*'],
    });

    new cdk.CfnOutput(this, 'SellerApiUrl', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'Set as SELLER_API_URL and X402_SELLER_CLOUDFRONT_URL in payer-agent .env',
      exportName: 'X402SellerApiUrl',
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: distribution.distributionId,
      exportName: 'X402DistributionId',
    });

    new cdk.CfnOutput(this, 'DistributionArn', {
      value: `arn:aws:cloudfront::${this.account}:distribution/${distribution.distributionId}`,
      description: 'CloudFront Distribution ARN — needed for WAF cleanup',
      exportName: 'X402DistributionArn',
    });
  }
}
