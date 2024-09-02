#### To get the terraform plan output file to analyse, use the following commands:
```
terraform plan -var-file="<tfvars file name>" -out=Pplan
```
##### or
```
terraform plan -out=Pplan
```
#### depending on your scenario, and then:
```
terraform show -no-color -json Pplan > terraform_plan.json
```
> Make sure that the json file is UTF-8 for this code to work at the moment
