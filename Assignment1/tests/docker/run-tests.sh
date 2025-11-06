#!/bin/bash

###############################################################################
# P2P Performance Test Runner - Docker Edition
# Chạy tất cả test trong Docker containers
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Config
COMPOSE_FILE="docker-compose.yml"
TEST_CONTAINER="p2p-test-runner"

print_msg() {
    color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo ""
    echo "========================================================================"
    print_msg "$BLUE" "$1"
    echo "========================================================================"
    echo ""
}

check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_msg "$RED" "ERROR: Docker is not running!"
        exit 1
    fi
}

setup_env() {
    if [ ! -f ".env" ]; then
        print_msg "$YELLOW" "No .env file found. Creating from .env.example..."
        if [ -f "../.env.example" ]; then
            cp ../.env.example .env
            print_msg "$GREEN" "✓ .env file created"
        else
            print_msg "$RED" "ERROR: .env.example not found in tests directory!"
            exit 1
        fi
    else
        print_msg "$GREEN" "✓ .env file exists"
    fi
}

start_services() {
    print_header "Starting Services"
    
    setup_env
    
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_msg "$YELLOW" "Waiting for server to be ready..."
    sleep 5
    
    for i in {1..30}; do
        if docker-compose -f "$COMPOSE_FILE" exec -T server python -c "import socket; s = socket.socket(); s.connect(('localhost', 9000)); s.close()" 2>/dev/null; then
            print_msg "$GREEN" "✓ Server is ready"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_msg "$RED" "ERROR: Server failed to start"
    exit 1
}

stop_services() {
    print_header "Stopping Services"
    docker-compose -f "$COMPOSE_FILE" down
    print_msg "$GREEN" "✓ Services stopped"
}

run_test() {
    local mode=$1
    print_header "Running $mode Test"
    
    docker exec -it "$TEST_CONTAINER" \
        python test_runner.py --mode "$mode" --server-host p2p-server
}

show_logs() {
    local service=${1:-}
    if [ -z "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" logs --tail=100
    else
        docker-compose -f "$COMPOSE_FILE" logs --tail=100 "$service"
    fi
}

show_results() {
    print_header "Test Results"
    
    if [ -d "./results" ] && [ "$(ls -A ./results 2>/dev/null)" ]; then
        echo "Latest results:"
        ls -lht ./results/ | head -20
    else
        print_msg "$YELLOW" "No results found"
    fi
}

shell() {
    docker exec -it "$TEST_CONTAINER" /bin/bash
}

clean() {
    print_header "Cleaning Up"
    
    docker-compose -f "$COMPOSE_FILE" down -v
    
    read -p "Remove Docker images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down --rmi all
    fi
    
    read -p "Remove test results? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ../results/*
        print_msg "$GREEN" "✓ Results cleaned"
    fi
    
    print_msg "$GREEN" "✓ Cleanup complete"
}

show_help() {
    cat << EOF
P2P Performance Testing - Docker Edition

Usage: $0 [command]

Commands:
    start           Start all services (server, APIs, test container)
    stop            Stop all services
    
    quick           Run quick test (~10 minutes)
                    - 1k clients scalability
                    - 5 clients P2P transfer
    
    standard        Run standard test (~30 minutes) [DEFAULT]
                    - 1k, 10k clients scalability
                    - 20 clients P2P transfer
                    - Heartbeat optimization
                    - Duplicate detection
    
    full            Run full test suite (2-3 hours)
                    - 1k, 10k, 100k clients scalability
                    - 20 clients P2P transfer
                    - Heartbeat optimization
                    - Duplicate detection
    
    logs [service]  Show logs (optional: specify service name)
    results         Show test results
    shell           Open interactive shell in test container
    clean           Clean up containers, images, and results
    
    help            Show this help message

Quick Start:
    $0 start        # Start services
    $0 quick        # Run quick test
    $0 results      # View results
    $0 stop         # Stop services

Examples:
    $0 quick                    # Quick validation
    $0 standard                 # Standard performance test
    $0 full                     # Complete test suite
    $0 logs server              # View server logs
    $0 shell                    # Open shell for debugging

Environment:
    Tests run in isolated Docker containers
    Results saved to ../results/
    Network: 172.25.0.0/16

EOF
}

main() {
    case "${1:-help}" in
        start)
            check_docker
            start_services
            ;;
        stop)
            stop_services
            ;;
        quick)
            check_docker
            start_services
            run_test "quick"
            ;;
        standard)
            check_docker
            start_services
            run_test "standard"
            ;;
        full)
            check_docker
            start_services
            run_test "full"
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        results)
            show_results
            ;;
        shell)
            check_docker
            shell
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_msg "$RED" "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
