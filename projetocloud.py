#based on code from https://blog.ipswitch.com/how-to-create-an-ec2-instance-with-python
import boto3
import os
import bcolors
from botocore.exceptions import ClientError
import time

ec2_nv = boto3.resource('ec2', 'us-east-1')
ec2_oh = boto3.resource('ec2', 'us-east-2')

# variables for North Virginia
nv_region = "us-east-1"
nv_ami = "ami-00ddb0e5626798373"

# variables for Ohio
region_oh = "us-east-2"
ami_oh = "ami-0dd9f0e7df0f0a138"

client_nv = boto3.client('ec2', 'us-east-1')
client_oh = boto3.client('ec2', 'us-east-2')
client_lb = boto3.client('elbv2', 'us-east-1')
client_as = boto3.client('autoscaling', 'us-east-1')

# Checks if the key already exists locally, if it does deletes it
def checks_if_key_exists_locally_then_deletes(key_name):
     if os.path.exists(key_name + '.pem'):
          os.remove(key_name + '.pem')  
          print("Existed locally, successfully deleted")
     else:
          print("Doesn't exist locally")

# Checks if the key already exists remotely, if it does deletes it
def checks_if_key_exists_remotely_then_deletes(key_name, client):
     # getting all key pairs
     keypairs = client.describe_key_pairs()

     for key in keypairs['KeyPairs']:
          if key['KeyName'] == key_name:
               response = client.delete_key_pair(
                    KeyName= key['KeyName']
               )
               print("Existed remotely, successfully deleted")

def create_key(ec2, key_name, client):
     # create a file to store the key locally
     outfile = open(key_name + '.pem','w')

     # call the boto ec2 function to create a key pair
     key_pair = ec2.create_key_pair(KeyName=key_name)

     # capture the key and store it in a file
     KeyPairOut = str(key_pair.key_material)
     outfile.write(KeyPairOut)
     outfile.close()
     print("Key created locally and remotely")

def security_groups_create_postgres(client, security_group_name, VPC_id):
     try:
          response = client.create_security_group(GroupName=security_group_name,
                                                  Description="Projeto Mayra",
                                                  VpcId = VPC_id)
          security_group_id = response['GroupId']

          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {
                         'IpProtocol' : 'tcp',
                         'FromPort' : 5432,
                         'ToPort' : 5432,
                         'IpRanges' : [{'CidrIp' : '0.0.0.0/0'}]
                    }
               ]
          )
          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {'IpProtocol': 'tcp', 
                        'FromPort': 22, 
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }]
          )
          return security_group_id

     except ClientError as e:
          print(e)

def security_groups_create_orm(client, security_group_name, VPC_id):
     try:
          response = client.create_security_group(GroupName=security_group_name,
                                                  Description="Projeto Mayra",
                                                  VpcId = VPC_id)
          security_group_id = response['GroupId']

          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {
                         'IpProtocol' : 'tcp',
                         'FromPort' : 8080,
                         'ToPort' : 8080,
                         'IpRanges' : [{'CidrIp' : '0.0.0.0/0'}]
                    }
               ]
          )
          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {'IpProtocol': 'tcp', 
                        'FromPort': 22, 
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }]
          )
          return security_group_id

     except ClientError as e:
          print(e)

def security_groups_create_loadbalancer(client, security_group_name, VPC_id):
     try:
          response = client.create_security_group(GroupName=security_group_name,
                                             Description="Projeto Mayra",
                                             VpcId = VPC_id)
          security_group_id = response['GroupId']

          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {
                    'IpProtocol' : 'tcp',
                    'FromPort' : 8080,
                    'ToPort' : 8080,
                    'IpRanges' : [{'CidrIp' : '0.0.0.0/0'}]
                    }
               ]
          )

          response = client.authorize_security_group_ingress(
               GroupId=security_group_id,
               IpPermissions=[
                    {'IpProtocol': 'tcp', 
                        'FromPort': 22, 
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }]
          )

          return security_group_id

     except ClientError as e:
          print(e)

def security_groups(client, security_group_name):
     response = client.describe_vpcs()
     VPC_id = response['Vpcs'][0]['VpcId']
     if security_group_name == 'security_db':
          security_id = security_groups_create_postgres(client, security_group_name, VPC_id)
     elif security_group_name == 'security_orm': 
          security_id = security_groups_create_orm(client, security_group_name, VPC_id)
     elif security_group_name == 'security_loadbalancer': 
          security_id = security_groups_create_loadbalancer(client, security_group_name, VPC_id)
     else:
          print('nao deu certo nao')

def security_group_delete(ec2, client, security_group_name):
     security_group_id = ''

     try:
          security_groups = client.describe_security_groups()
          for sg in security_groups['SecurityGroups']:
               if sg['GroupName'] == security_group_name:
                    security_group_id = sg['GroupId']
          client.delete_security_group(GroupId=security_group_id)
          print('Security group deleted successfully!')
     except ClientError as e:
          print("Security group didn't exist")

def delete_instances(ec2, client, key):
     all_deleted = False
     response = client.describe_instances(Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                key,
            ]
        },
     ])
     instances_ids = []
     for each in response['Reservations']:
          instances_ids.append(each['Instances'][0]['InstanceId'])
     ec2.instances.filter(InstanceIds = instances_ids).terminate()
     while not all_deleted:
          all_deleted = True
          response = client.describe_instances(Filters=[
               {
                    'Name': 'tag:Name',
                    'Values': [
                         key,
                    ]
               },
          ])
          instances_ids = []
          for each in response['Reservations']:
               if each['Instances'][0]['State']['Name'] != 'terminated':
                    all_deleted = False

     print("All instances were deleted successfully")

def create_instance(ec2, client, ami, key_name, security_group_name, userdata):
     found = False
     # create a new EC2 instance
     instance = ec2.create_instances(
          ImageId=ami,
          MinCount=1,
          MaxCount=1,
          InstanceType='t2.micro',
          KeyName=key_name,
          SecurityGroups=[
            security_group_name,
          ], 
          TagSpecifications=[{
               'ResourceType' : 'instance',
               'Tags' : [
                    {
                         'Key' : 'Name',
                         'Value' : key_name,
                    },
                    {
                         'Key' : 'Owner',
                         'Value' : 'mayra.peter'
                    }
               ]
          }],
          UserData=userdata
     )
     while not found:
          response = client.describe_instances(Filters=[
          {
               'Name': 'tag:Name',
               'Values': [
                    key_name,
               ]
          },
          ])

          db_ip =''
          for each in response['Reservations']:
               if each['Instances'][0]['State']['Name'] == 'running':
                    found = True
                    db_ip = each['Instances'][0]['PublicIpAddress']
                    instance_id= each['Instances'][0]['InstanceId']
                    
     return instance_id, db_ip

def delete_ami(client, ami_name):
     response = client.describe_images(
          Filters=[
               {
                    'Name': 'tag:Name',
                    'Values': [
                         'customizedAMI',
                    ]
               },
          ],
     )
     print("as amis sao", response)

     # response = client.deregister_image(
     #      ImageId = ami_id,
     # )    

def create_ami(client, key_name, ami_name):
     
     found = False

     while not found:
          response = client.describe_instances(Filters=[
               {
                    'Name': 'tag:Name',
                    'Values': [
                         key_name,
                    ]
               },
          ])

          ami_id = ''
          for each in response['Reservations']:
               if each['Instances'][0]['State']['Name'] == 'running':
                    found = True
                    db_ip = each['Instances'][0]['PublicIpAddress']
                    instance_id= each['Instances'][0]['InstanceId']
                    ami_id = client_nv.create_image(InstanceId=instance_id, Name=ami_name)
                    return ami_id
     return ami_id

def create_loadbalancer(client, client_lb, security_group_name):
     security_group_id = client.describe_security_groups(GroupNames=[security_group_name])["SecurityGroups"][0]["GroupId"]
     response = client.describe_subnets()
     subnets = []
     for subnet in response['Subnets']:
          subnets.append(subnet['SubnetId'])
          print(subnet['SubnetId'])
     response = client_lb.create_load_balancer(
          Name='mayra-loadbalancer',
          Subnets=[
               subnets[0],
               subnets[1],
               subnets[2],
               subnets[3],
               subnets[4],
               subnets[5],
          ],
          SecurityGroups=[
               security_group_id,
          ],
          Scheme='internet-facing',
          Tags=[
               {
                    'Key': 'Owner',
                    'Value': 'mayra.peter'
               },
          ],
          Type='application',
          IpAddressType='ipv4'
     )
     lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']

     waiter = client_lb.get_waiter('load_balancer_exists')
     waiter.wait(LoadBalancerArns=[lb_arn])
     time.sleep(15)

     return lb_arn

def create_target_group(client, client_lb):
     response = client.describe_vpcs()
     VPC_id = response['Vpcs'][0]['VpcId']
    
     response = client_lb.create_target_group(
          Name = 'mayra-tg',
          Protocol = 'HTTP',
          Port = 8000,
          VpcId = VPC_id,
          HealthCheckProtocol = 'HTTP',
          HealthCheckPath = '/healthcheck',
          TargetType='instance'
     )

     response = client_lb.describe_target_groups(
          Names=[
               'mayra-tg',
          ]
     )
     arn = response["TargetGroups"][0]["TargetGroupArn"]

     return arn

def create_listener(client_lb, lb_arn, tg_arn):
     response = client_lb.create_listener(
               LoadBalancerArn = lb_arn,
               Protocol='HTTP',
               Port=8000,
               DefaultActions=[
                    {
                         'Type': 'forward',
                         'TargetGroupArn': tg_arn
                    }
               ])

def create_autoscaling(client_as, tg_arn, instance_id):
     response = client_as.create_auto_scaling_group(
     AutoScalingGroupName='MayAutoscaling',
     MinSize=1,
     MaxSize=3,
     InstanceId = instance_id,
     DesiredCapacity=1,
     TargetGroupARNs=[
          tg_arn,
     ],
     Tags=[
          {
               'Key'  : 'Name',
               'Value': 'MayAutoscaling' 
          }]     
     )

def delete_autoscaling(client):
     response = client.delete_auto_scaling_group(
          AutoScalingGroupName='MayAutoscaling',
          ForceDelete=True
     )

          

userdata_oh = '''#!/bin/bash
               sudo apt update
               sudo apt install postgresql postgresql-contrib -y
               sudo -u postgres psql -c "CREATE USER mayra WITH PASSWORD 'mayra';"
               sudo -u postgres createdb -O mayra tasks
               sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/10/main/postgresql.conf
               echo "host    all         all         0.0.0.0/0             trust" >> /etc/postgresql/10/main/pg_hba.conf
               sudo ufw allow 5432/tcp
               sudo systemctl restart postgresql
               '''
               
checks_if_key_exists_locally_then_deletes('ec2-keypair_oh')
checks_if_key_exists_remotely_then_deletes('ec2-keypair_oh', client_oh)
create_key(ec2_oh, 'ec2-keypair_oh', client_oh)
delete_instances(ec2_oh, client_oh, 'ec2-keypair_oh')
security_group_delete(ec2_oh, client_oh, 'security_db')
security_groups(client_oh, 'security_db')
instance_oh_id, db_ip = create_instance(ec2_oh, client_oh, ami_oh, 'ec2-keypair_oh', 'security_db', userdata_oh)

userdata_nv = '''#!/bin/bash
               cd /home/ubuntu
               sudo apt update
               git clone https://github.com/mayrapeter/tasks
               cd tasks
               sudo sed -i 's/xxxx/{}/g' /home/ubuntu/tasks/portfolio/settings.py
               ./install.sh
               sudo reboot
               '''.format(db_ip)

checks_if_key_exists_locally_then_deletes('ec2-keypair_nv')
checks_if_key_exists_remotely_then_deletes('ec2-keypair_nv', client_nv)
create_key(ec2_nv, 'ec2-keypair_nv', client_nv)
delete_instances(ec2_nv, client_nv, 'ec2-keypair_nv')
security_group_delete(ec2_nv, client_nv,'security_orm')
security_group_delete(ec2_nv, client_nv, 'security_loadbalancer')
security_groups(client_nv, 'security_loadbalancer')
security_groups(client_nv, 'security_orm')
instance_nv_id = create_instance(ec2_nv, client_nv, nv_ami, 'ec2-keypair_nv', 'security_orm', userdata_nv)[0]

delete_ami(client_nv, 'customizedAMI')
#ami_id = create_ami(client_nv, 'ec2-keypair_nv', 'customizedAMI')
#delete_instances(ec2_nv, client_nv, 'ec2-keypair_nv')

lb_arn = create_loadbalancer(client_nv, client_lb, 'security_loadbalancer')
tg_arn = create_target_group(client_nv, client_lb)
create_listener(client_lb, lb_arn, tg_arn)
delete_autoscaling(client_as)
create_autoscaling(client_as, tg_arn, instance_nv_id)





