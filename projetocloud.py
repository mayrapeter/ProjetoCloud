import boto3
import os
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

def delete_file_dns(name):
     if os.path.exists(name + '.txt'):
          os.remove(name + '.txt')  
          print(" DNS file existed locally, successfully deleted")
     else:
          print("DNS file didn't exist locally")

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

# Creates key
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

def create_file_dns(lb_dns, name):
     outfile = open(name + '.txt','w')
     outfile.write(lb_dns)
     outfile.close()
     print("Load balancer file created successfully")

# Creates the security group for the DB instance
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

# Creates the security group for the ORM instance
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

# Creates the security group for the loadbalancer instance
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

# Creates the right security group
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
          print('Nome do security group desconhecido')

# Deletes the right security group
def security_group_delete(ec2, client, security_group_name):
     security_group_id = ''

     try:
          security_groups = client.describe_security_groups()
          for sg in security_groups['SecurityGroups']:
               if sg['GroupName'] == security_group_name:
                    security_group_id = sg['GroupId']
          try:
               client.delete_security_group(GroupId=security_group_id)
               print('Security group deleted successfully!')
          except ClientError as e:
               print("Couldn't delete security group")
     except ClientError as e:
          print("Security group didn't exist")

# Deletes the right instances 
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

# Creates instance
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

# Creates loadbalancer
def create_loadbalancer(client, client_lb, security_group_name):
     security_group_id = client.describe_security_groups(GroupNames=[security_group_name])["SecurityGroups"][0]["GroupId"]
     response = client.describe_subnets()
     subnets = []
     for subnet in response['Subnets']:
          subnets.append(subnet['SubnetId'])
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
     lb_dns = response['LoadBalancers'][0]['DNSName']

     waiter = client_lb.get_waiter('load_balancer_exists')
     waiter.wait(LoadBalancerArns=[lb_arn])
     time.sleep(20)

     return lb_arn, lb_dns

# Deletes the loadbalancer
def delete_loadbalancer(client):
     erased = 0
     arn = ''
     response = client.describe_load_balancers()
     for lb in response['LoadBalancers']:
          if lb['LoadBalancerName'] == 'mayra-loadbalancer':
               arn = lb['LoadBalancerArn']
               client.delete_load_balancer(
                    LoadBalancerArn=arn
               ) 
     while erased == 0:
          erased = 1
          response1 = client.describe_load_balancers()
          for lb in response1['LoadBalancers']:
               if lb['LoadBalancerName'] == 'mayra-loadbalancer':
                    erased = 0
     print("Load Balancer deleted successfully")

# Deletes the target group
def delete_target_group(client):
     response = client.describe_target_groups()
     for tg in response['TargetGroups']:
          if tg['TargetGroupName'] == 'mayra-tg':
               try:
                    response = client.delete_target_group(
                         TargetGroupArn=tg['TargetGroupArn']
                    )
                    print("deleted target group")
               except ClientError as e:
                    print(e)

# Creates the target group
def create_target_group(client, client_lb):
     response = client.describe_vpcs()
     VPC_id = response['Vpcs'][0]['VpcId']
    
     response = client_lb.create_target_group(
          Name = 'mayra-tg',
          Protocol = 'HTTP',
          Port = 8080,
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

# Creates listener
def create_listener(client_lb, lb_arn, tg_arn):
     response = client_lb.create_listener(
               LoadBalancerArn = lb_arn,
               Protocol='HTTP',
               Port=8080,
               DefaultActions=[
                    {
                         'Type': 'forward',
                         'TargetGroupArn': tg_arn
                    }
               ])

# Deletes listener
def delete_listener(client):
     lb_arn = ''
     response = client.describe_load_balancers()
     for lb in response['LoadBalancers']:
          if lb['LoadBalancerName'] == 'mayra-loadbalancer':
               lb_arn = lb['LoadBalancerArn']
     if lb_arn != '':
          response = client.describe_listeners(LoadBalancerArn=lb_arn)
          
          for listener in response['Listeners']:
               if listener['LoadBalancerArn'] == lb_arn:
                    print("Found the right listener")
                    try:
                         response = client.delete_listener(
                              ListenerArn=listener['ListenerArn']
                         )
                    except ClientError as e:
                         print(e)
     else: 
          print("Load Balancer wasn't found")

# Creates autoscaling
def create_autoscaling(client_as, tg_arn, instance_id):
     erased = 0
     #esperando ate que seja realmente deletada
     while erased == 0: 
          response = client_as.describe_auto_scaling_groups()
          erased = 1
          for asg in response['AutoScalingGroups']:
               if asg['AutoScalingGroupName'] == 'MayAutoscaling':
                    erased = 0
     try:
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
     except ClientError as e:
          print(e)
     
# Deletes autoscaling
def delete_autoscaling(client):
     response = client.describe_auto_scaling_groups()
     for asg in response['AutoScalingGroups']:
          if asg['AutoScalingGroupName'] == 'MayAutoscaling':
               response2 = client.delete_auto_scaling_group(
                    AutoScalingGroupName='MayAutoscaling',
                    ForceDelete=True
               )
     print("Autoscaling deleted successfully")

# Deletes launch configuration
def delete_launch_configuration(client):
     try:
          response = client.delete_launch_configuration(
          LaunchConfigurationName='MayAutoscaling'
     )   
     except ClientError as e:
          print(e)

# Userdata to create the DB instance
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

# Userdata to create the ORM instance
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
delete_file_dns("dns_loadbalancer")
delete_autoscaling(client_as)
delete_launch_configuration(client_as)
delete_listener(client_lb)
delete_loadbalancer(client_lb)
delete_target_group(client_lb)
delete_instances(ec2_nv, client_nv, 'ec2-keypair_nv')
security_group_delete(ec2_nv, client_nv,'security_orm')
security_group_delete(ec2_nv, client_nv, 'security_loadbalancer')
security_groups(client_nv, 'security_loadbalancer')
security_groups(client_nv, 'security_orm')
instance_nv_id = create_instance(ec2_nv, client_nv, nv_ami, 'ec2-keypair_nv', 'security_orm', userdata_nv)[0]

lb_arn, lb_dns = create_loadbalancer(client_nv, client_lb, 'security_loadbalancer')
create_file_dns(lb_dns, "dns_loadbalancer")
tg_arn = create_target_group(client_nv, client_lb)
create_listener(client_lb, lb_arn, tg_arn)
create_autoscaling(client_as, tg_arn, instance_nv_id)





