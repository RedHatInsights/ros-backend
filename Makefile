help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo ""
	@echo "--- Commands for local development ---"
	@echo "insights-upload-data                    upload data to local ingress service for ROS processing"
	@echo "api-get-hosts                           get list of systems"
	@echo "get-all-suggested-instance-types        get all suggested instance types"
	@echo "produce-no-pcp-message			produce no pcp message to the HBI topic"
	@echo "listen-report-processor-event	        listens to ros.events topic"
	@echo "produce-system-delete-event                    send delete event message to test system eraser (use DELETE_SYSTEM_ID=<id> to specify custom ID)"

metadata={"branch_info": {"remote_branch": -1, "remote_leaf": -1}, "bios_uuid": "25d6ad97-60fa-4d3e-b2cc-4aa437c28f71", "ip_addresses": ["10.74.255.52", "2620:52:0:4af8:21a:4aff:fe00:a8a"], "fqdn": "vm255-52.gsslab.pnq2.redhat.com", "mac_addresses": ["00:1a:4a:00:0a:8a", "00:00:00:00:00:00"], "satellite_id": -1, "subscription_manager_id": "7846d4fa-6fcc-4b84-aa13-5f12e588ecca", "insights_id": "1d42f242-3828-4a00-8009-c67656c86a51", "machine_id": "25d6ad97-60fa-4d3e-b2cc-4aa437c28f71"}
identity={"identity": {"account_number": "0000001", "org_id": "000001", "auth_type": "jwt-auth", "type": "User","user": {"username": "tuser@redhat.com","email": "tuser@redhat.com","first_name": "test","last_name": "user","is_active": true,"is_org_admin": false, "locale": "en_US"}}}

b64_identity=$(shell echo '${identity}' | base64 -w 0 -)
ROS_API_PORT?=8000

insights-upload-data:
	curl -v -F "upload=@sample-files/rhel8/rhel8-insights-ip-aws-idle.tar.gz;type=application/vnd.redhat.advisor.collection+tgz" \
	    -H "x-rh-identity: ${b64_identity}" \
		-H "x-rh-request_id: testtesttest" \
		localhost:3000/api/ingress/v1/upload | python -m json.tool

api-get-hosts:
	curl -v -H "Content-Type: application/json"  -H "x-rh-identity: ${b64_identity}" "localhost:${ROS_API_PORT}/api/ros/v1/systems?order_by=max_io&order_how=DESC" | python -m json.tool

get-all-suggested-instance-types:
	curl -v -H "Content-Type: application/json"  -H "x-rh-identity: ${b64_identity}" "localhost:${ROS_API_PORT}/api/ros/v1/suggested_instance_types" | python -m json.tool

produce-no-pcp-message:
	kcat -b localhost:9092 -t platform.inventory.events -P sample-files/no_pcp_raw_message.json

produce-api-message:
	kcat -b localhost:9092 -t platform.inventory.events -P sample-files/api_message.json -H "producer=host-inventory-service"

listen-report-processor-event:
	kcat -b localhost:29092 -t ros.events -C -o end

produce-system-delete-event:
	$(eval DELETE_SYSTEM_ID ?= bdc9eb93-b636-4663-a9fe-47db34cb5ca4)
	jq -c '.id = "$(DELETE_SYSTEM_ID)"' sample-files/delete_system_message.json | kcat -b localhost:9092 -t platform.inventory.events -P

get_unleash_features:
	curl -H "Authorization: ros:dev.token" http://localhost:3063/api/client/features && echo
