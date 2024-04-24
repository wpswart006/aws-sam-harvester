import boto3
import os
import yaml
import re

from zipfile import ZipFile

LAMBDA_FUNCTION_TYPE="AWS::Serverless::Function"
STEP_FUNCTION_TYPE="AWS::Serverless::StateMachine"

s3 = boto3.client('s3')

def pascal_to_camel(input: str)-> str:

    return re.sub(r'(?<!^)(?=[A-Z])', '_', input).lower()

def main() -> None:
    with open("template.yaml") as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
        os.mkdir(f"lambda_functions")
    
    for key, value in data["Resources"].items():
        
        if value["Type"] == LAMBDA_FUNCTION_TYPE:
            folder_name = pascal_to_camel(key)
            
            try:
                os.mkdir(f"{folder_name}")
            except FileExistsError:
                continue
            s3_uri = value["Properties"]["CodeUri"]
            parts = s3_uri.split('/')
            bucket_name = parts[2]
            object_name = "/".join(parts[3:])
            file_name = parts[4]
            
            with open(f"{folder_name}/{file_name}", "wb") as fp:

                response = s3.get_object(
                    Bucket=bucket_name,
                    Key=object_name
                )
                fp.write(response["Body"].read())

            with ZipFile(f"{folder_name}/{file_name}", "r") as zf:
                zf.extractall(f"{folder_name}")

            os.remove(f"{folder_name}/{file_name}")
            data["Resources"][key]["Properties"]["CodeUri"] = f"{folder_name}/"
        elif value["Type"] == STEP_FUNCTION_TYPE:
            file_name = pascal_to_camel(key)
            bucket_name = value["Properties"]["DefinitionUri"]["Bucket"]
            object_name = value["Properties"]["DefinitionUri"]["Key"]

            file_path = f"stepfunctions/{file_name}.asl.json"
            with open(file_path, "wb") as fp:

                response = s3.get_object(
                    Bucket=bucket_name,
                    Key=object_name
                )

                fp.write(response["Body"].read())
            data["Resources"][key]["Properties"]["DefinitionUri"] = file_path
        
    with open("template.yaml", "w") as fp:
        yaml.safe_dump(data, fp)
    
            


if __name__ == "__main__":
    main()