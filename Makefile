PYTHON := python

SERVER_1_SOCKET_PATH := sockets/server_1.sock
SERVER_2_SOCKET_PATH := sockets/server_2.sock
SERVER_1_LOCK_FILE_PATH := locks/server_1.lock
SERVER_2_LOCK_FILE_PATH := locks/server_2.lock
SERVER_1_LOG_PIPE_PATH := pipes/server_1.pipe
SERVER_2_LOG_PIPE_PATH := pipes/server_2.pipe
SERVER_1_LOG_FILE_PATH := logs/server_1.log
SERVER_2_LOG_FILE_PATH := logs/server_2.log

run_servers: run_log_server_1 run_server_1 run_log_server_2 run_server_2
	@echo "[run_servers] Launching: log_server_1 -> server_1 -> log_server_2 -> server_2"


run_server_1:
	@echo "[run_server_1] PYTHON=$(PYTHON)"
	@echo "[run_server_1] SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH)"
	@echo "[run_server_1] LOCK_FILE_PATH=$(SERVER_1_LOCK_FILE_PATH)"
	@echo "[run_server_1] LOG_PIPE_PATH=$(SERVER_1_LOG_PIPE_PATH)"
	SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH) \
	LOCK_FILE_PATH=$(SERVER_1_LOCK_FILE_PATH) \
	LOG_PIPE_PATH=$(SERVER_1_LOG_PIPE_PATH) \
	$(PYTHON) src/server.py

run_server_2:
	@echo "[run_server_2] PYTHON=$(PYTHON)"
	@echo "[run_server_2] SERVER_SOCKET_PATH=$(SERVER_2_SOCKET_PATH)"
	@echo "[run_server_2] LOCK_FILE_PATH=$(SERVER_2_LOCK_FILE_PATH)"
	@echo "[run_server_2] LOG_PIPE_PATH=$(SERVER_2_LOG_PIPE_PATH)"
	SERVER_SOCKET_PATH=$(SERVER_2_SOCKET_PATH) \
	LOCK_FILE_PATH=$(SERVER_2_LOCK_FILE_PATH) \
	LOG_PIPE_PATH=$(SERVER_2_LOG_PIPE_PATH) \
	$(PYTHON) src/server.py

run_log_server_1:
	@echo "[run_log_server_1] PYTHON=$(PYTHON)"
	@echo "[run_log_server_1] LOG_PIPE_PATH=$(SERVER_1_LOG_PIPE_PATH)"
	@echo "[run_log_server_1] LOG_FILE_PATH=$(SERVER_1_LOG_FILE_PATH)"
	LOG_PIPE_PATH=$(SERVER_1_LOG_PIPE_PATH) \
	LOG_FILE_PATH=$(SERVER_1_LOG_FILE_PATH) \
	$(PYTHON) src/log_server.py

run_log_server_2:
	@echo "[run_log_server_2] PYTHON=$(PYTHON)"
	@echo "[run_log_server_2] LOG_PIPE_PATH=$(SERVER_2_LOG_PIPE_PATH)"
	@echo "[run_log_server_2] LOG_FILE_PATH=$(SERVER_2_LOG_FILE_PATH)"
	LOG_PIPE_PATH=$(SERVER_2_LOG_PIPE_PATH) \
	LOG_FILE_PATH=$(SERVER_2_LOG_FILE_PATH) \
	$(PYTHON) src/log_server.py

run_cli_client:
	@echo "[run_cli_client] PYTHON=$(PYTHON)"
	@echo "[run_cli_client] SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH)"
	SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH) \
	$(PYTHON) src/cli_client.py

run_cli_client_docker:
	docker compose run --build --rm cli_client

run_web_client:
	@echo "[run_web_client] PYTHON=$(PYTHON)"
	@echo "[run_web_client] SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH)"
	SERVER_SOCKET_PATH=$(SERVER_1_SOCKET_PATH) \
	$(PYTHON) src/web_client.py

run_web_client_docker:
	docker compose run --build --rm -d web_client