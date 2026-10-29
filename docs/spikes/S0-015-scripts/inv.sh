#!/bin/bash
# usage: inv.sh <function> <json payload>
F=$1; P=$2; O=$(mktemp); export PYTHONIOENCODING=utf-8
aws lambda invoke --region ap-northeast-1 --function-name "$F" --cli-binary-format raw-in-base64-out --payload "$P" --log-type Tail --query '{status:StatusCode,err:FunctionError,log:LogResult}' --output json "$O" > "$O.meta"
if grep -q '"err": "' "$O.meta"; then echo "ERROR:"; python -I -c "import json,base64,sys;m=json.load(open(sys.argv[1]));print(base64.b64decode(m['log']).decode()[-1500:])" "$O.meta"; fi
cat "$O"; echo
python -I -c "import json,base64,sys;m=json.load(open(sys.argv[1]));print('   REPORT:', [l for l in base64.b64decode(m['log']).decode().splitlines() if l.startswith('REPORT')][0].replace('\t',' | ')[:220])" "$O.meta"
rm -f "$O" "$O.meta"
