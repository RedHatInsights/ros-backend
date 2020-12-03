help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo ""
	@echo "--- Commands for local development ---"
	@echo "insights-upload-data       upload data to local ingress service for ROS processing"

insights-upload-data:
	curl -vvvv -F "upload=@sample.tar.gz;type=application/vnd.redhat.resource-optimization.sample+tgz" \
		-H "x-rh-identity: eyJpZGVudGl0eSI6IHsiYWNjb3VudF9udW1iZXIiOiAiMTIzNDUiLCAiaW50ZXJuYWwiOiB7Im9yZ19pZCI6ICI1NDMyMSJ9fX0=" \
		-H "x-rh-request_id: testtesttest" \
		localhost:8080/api/ingress/v1/upload