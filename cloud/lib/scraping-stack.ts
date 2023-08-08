import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DockerImageFunction, DockerImageCode } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import * as path from 'path';

export class CloudStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const amazon_scraping_lambda = new DockerImageFunction(this, "AmazonScrapingFunction",{
      code: DockerImageCode.fromImageAsset(path.join(__dirname, '../../backend_services/scraping/amazon/'))
    })

  }
}
