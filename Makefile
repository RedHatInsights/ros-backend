help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo ""
	@echo "--- Commands for local development ---"
	@echo "insights-upload-data       upload data to local ingress service for ROS processing"

metadata={"branch_info": {"remote_branch": -1, "remote_leaf": -1}, "bios_uuid": "25d6ad97-60fa-4d3e-b2cc-4aa437c28f71", "ip_addresses": ["10.74.255.52", "2620:52:0:4af8:21a:4aff:fe00:a8a"], "fqdn": "vm255-52.gsslab.pnq2.redhat.com", "mac_addresses": ["00:1a:4a:00:0a:8a", "00:00:00:00:00:00"], "satellite_id": -1, "subscription_manager_id": "7846d4fa-6fcc-4b84-aa13-5f12e588ecca", "insights_id": "5ae6c008-b6b3-459b-82a0-7ebf75a047fd", "machine_id": "25d6ad97-60fa-4d3e-b2cc-4aa437c28f71"}

ros-upload-data:
	curl -vvvv -F "upload=@sample-files/ros-sample.tar.gz;type=application/vnd.redhat.resource-optimization.sample+tgz" -F 'metadata=${metadata}' \
		-H "x-rh-identity: eyJpZGVudGl0eSI6IHsiYWNjb3VudF9udW1iZXIiOiAiMDAwMDAwMSIsICJ0eXBlIjogIlVzZXIiLCAiaW50ZXJuYWwiOiB7Im9yZ19pZCI6ICIwMDAwMDEifX19Cg==" \
		-H "x-rh-request_id: testtesttest" \
		localhost:3000/api/ingress/v1/upload

insights-upload-data:
	curl -vvvv -F "upload=@sample-files/insights-aws-sample.tar.gz;type=application/vnd.redhat.advisor.collection+tgz" \
	    -H "x-rh-identity: eyJpZGVudGl0eSI6IHsiYWNjb3VudF9udW1iZXIiOiAiMDAwMDAwMSIsICJ0eXBlIjogIlVzZXIiLCAiaW50ZXJuYWwiOiB7Im9yZ19pZCI6ICIwMDAwMDEifX19Cg==" \
		-H "x-rh-request_id: testtesttest" \
		localhost:3000/api/ingress/v1/upload