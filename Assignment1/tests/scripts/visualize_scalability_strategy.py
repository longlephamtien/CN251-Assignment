#!/usr/bin/env python3
"""
Visualize Docker Multi-Container Scalability Strategy
Tạo diagram cho báo cáo
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_architecture_diagram():
    """Tạo diagram kiến trúc multi-container"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(7, 9.5, 'Docker Multi-Container Scalability Architecture', 
            ha='center', va='top', fontsize=16, fontweight='bold')
    
    # Host Machine
    host_box = FancyBboxPatch((0.2, 0.2), 13.6, 9, 
                              boxstyle="round,pad=0.1", 
                              edgecolor='black', facecolor='lightgray', 
                              linewidth=2, alpha=0.3)
    ax.add_patch(host_box)
    ax.text(0.5, 8.8, 'Host Machine', fontsize=12, fontweight='bold')
    
    # Docker Network
    network_box = FancyBboxPatch((0.5, 0.5), 13, 7.8,
                                 boxstyle="round,pad=0.1",
                                 edgecolor='blue', facecolor='lightblue',
                                 linewidth=2, alpha=0.2)
    ax.add_patch(network_box)
    ax.text(7, 8, 'Docker Network (172.30.0.0/16)', 
            ha='center', fontsize=11, style='italic')
    
    # Server
    server_box = FancyBboxPatch((5.5, 6.5), 3, 1.2,
                                boxstyle="round,pad=0.1",
                                edgecolor='darkgreen', facecolor='lightgreen',
                                linewidth=2)
    ax.add_patch(server_box)
    ax.text(7, 7.3, 'P2P Server', ha='center', fontsize=11, fontweight='bold')
    ax.text(7, 7, '172.30.0.10:9000', ha='center', fontsize=9)
    ax.text(7, 6.7, '8 CPUs, 32GB RAM', ha='center', fontsize=8, style='italic')
    
    # Client Containers
    container_y_start = 3
    container_spacing = 1.8
    num_visible = 4
    
    for i in range(num_visible):
        x = 1 + (i * 3.2)
        y = container_y_start
        
        # Container box
        cont_box = FancyBboxPatch((x, y), 2.8, 2,
                                  boxstyle="round,pad=0.05",
                                  edgecolor='darkblue', facecolor='lightyellow',
                                  linewidth=1.5)
        ax.add_patch(cont_box)
        
        # Container label
        ax.text(x + 1.4, y + 1.7, f'Container {i+1}', 
                ha='center', fontsize=9, fontweight='bold')
        ax.text(x + 1.4, y + 1.4, f'172.30.0.{11+i}', 
                ha='center', fontsize=8)
        
        # Client info
        ax.text(x + 1.4, y + 1.1, '1,000 clients', 
                ha='center', fontsize=8, color='darkred', fontweight='bold')
        ax.text(x + 1.4, y + 0.8, 'Ports: 6000-7000', 
                ha='center', fontsize=7)
        ax.text(x + 1.4, y + 0.5, '2 CPU, 4GB RAM', 
                ha='center', fontsize=7, style='italic')
        
        # Arrow to server
        arrow = FancyArrowPatch((x + 1.4, y + 2), (7, 6.5),
                               arrowstyle='->', mutation_scale=15,
                               color='gray', linewidth=1, alpha=0.6)
        ax.add_patch(arrow)
    
    # "..." indicator
    ax.text(12.5, container_y_start + 1, '...', 
            ha='center', fontsize=20, fontweight='bold')
    
    # Coordinator
    coord_box = FancyBboxPatch((5.5, 1), 3, 1,
                               boxstyle="round,pad=0.1",
                               edgecolor='purple', facecolor='lavender',
                               linewidth=2)
    ax.add_patch(coord_box)
    ax.text(7, 1.7, 'Test Coordinator', ha='center', fontsize=10, fontweight='bold')
    ax.text(7, 1.4, '172.30.0.20', ha='center', fontsize=8)
    ax.text(7, 1.1, 'Orchestrates Tests', ha='center', fontsize=7, style='italic')
    
    # Legend
    legend_y = 0.3
    ax.text(0.5, legend_y, 'Strategy:', fontsize=9, fontweight='bold')
    ax.text(0.5, legend_y - 0.2, '• Each container = isolated network namespace', fontsize=7)
    ax.text(0.5, legend_y - 0.4, '• Same port range (6000-7000) in each container', fontsize=7)
    ax.text(0.5, legend_y - 0.6, '• N containers = N × 1,000 clients capacity', fontsize=7)
    
    plt.tight_layout()
    plt.savefig('../results/docker_architecture.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: docker_architecture.png")
    plt.close()

def create_scaling_comparison():
    """So sánh scaling: Single machine vs Multi-container"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Single Machine Limitation
    ax1.set_title('Single Machine (Port Limited)', fontsize=12, fontweight='bold')
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    
    # Machine box
    machine_box = FancyBboxPatch((1, 1), 8, 8,
                                 boxstyle="round,pad=0.1",
                                 edgecolor='red', facecolor='mistyrose',
                                 linewidth=2)
    ax1.add_patch(machine_box)
    ax1.text(5, 8.5, 'Single Machine', ha='center', fontsize=11, fontweight='bold')
    
    # Port range
    ax1.text(5, 7.5, 'Ports: 6000-7000', ha='center', fontsize=10, 
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    ax1.text(5, 6.8, '1,001 ports total', ha='center', fontsize=9)
    
    # Clients
    clients_y = 5.5
    for i in range(10):
        x = 1.5 + (i * 0.7)
        rect = patches.Rectangle((x, clients_y), 0.5, 0.8, 
                                 linewidth=1, edgecolor='blue', facecolor='lightblue')
        ax1.add_patch(rect)
        if i < 3:
            ax1.text(x + 0.25, clients_y + 0.4, f'C{i+1}', 
                    ha='center', va='center', fontsize=7)
    
    ax1.text(7.5, clients_y + 0.4, '...', ha='center', fontsize=14, fontweight='bold')
    
    # Limitation
    ax1.text(5, 4, 'MAX: ~1,000 clients', ha='center', fontsize=11, 
             color='red', fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='white', edgecolor='red', linewidth=2))
    
    ax1.text(5, 3, '❌ Cannot test 10k clients', ha='center', fontsize=9, color='red')
    ax1.text(5, 2.5, '❌ Cannot test 100k clients', ha='center', fontsize=9, color='red')
    ax1.text(5, 2, '❌ Port exhaustion!', ha='center', fontsize=9, color='red')
    
    # Multi-Container Solution
    ax2.set_title('Multi-Container (Unlimited)', fontsize=12, fontweight='bold')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    
    # Containers
    container_positions = [(1, 6), (4, 6), (7, 6), (1, 3), (4, 3), (7, 3)]
    
    for i, (x, y) in enumerate(container_positions):
        if i < 5:
            cont_box = FancyBboxPatch((x, y), 2.5, 2,
                                     boxstyle="round,pad=0.05",
                                     edgecolor='green', facecolor='lightgreen',
                                     linewidth=1.5, alpha=0.7)
            ax2.add_patch(cont_box)
            ax2.text(x + 1.25, y + 1.5, f'Container {i+1}', 
                    ha='center', fontsize=8, fontweight='bold')
            ax2.text(x + 1.25, y + 1.1, 'Ports:', ha='center', fontsize=7)
            ax2.text(x + 1.25, y + 0.8, '6000-7000', ha='center', fontsize=7,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5, pad=0.2))
            ax2.text(x + 1.25, y + 0.4, '1k clients', ha='center', fontsize=7, color='blue')
        else:
            ax2.text(x + 1.25, y + 1, '...', ha='center', fontsize=20, fontweight='bold')
    
    # Calculation
    ax2.text(5, 1.5, 'N containers × 1,000 clients', ha='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='lightgreen', edgecolor='green', linewidth=2))
    
    ax2.text(5, 0.8, '✓ Test 10k = 10 containers', ha='center', fontsize=9, color='green')
    ax2.text(5, 0.4, '✓ Test 100k = 100 containers', ha='center', fontsize=9, color='green')
    ax2.text(5, 0, '✓ No port limit!', ha='center', fontsize=9, color='green', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('../results/scaling_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: scaling_comparison.png")
    plt.close()

def create_resource_chart():
    """Chart tài nguyên cần thiết cho các test modes"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    test_sizes = ['1k', '10k', '50k', '100k']
    containers = [1, 10, 50, 100]
    ram_gb = [3, 30, 150, 300]
    cpus = [1, 10, 50, 100]
    
    # RAM Chart
    bars1 = ax1.bar(test_sizes, ram_gb, color=['green', 'yellow', 'orange', 'red'], 
                    edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('RAM Required (GB)', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Test Size (clients)', fontsize=11, fontweight='bold')
    ax1.set_title('Memory Requirements', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add values on bars
    for i, (bar, val) in enumerate(zip(bars1, ram_gb)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val}GB\n({containers[i]} containers)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # CPU Chart
    bars2 = ax2.bar(test_sizes, cpus, color=['green', 'yellow', 'orange', 'red'],
                    edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('CPUs Required', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Test Size (clients)', fontsize=11, fontweight='bold')
    ax2.set_title('CPU Requirements', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    # Add values on bars
    for i, (bar, val) in enumerate(zip(bars2, cpus)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val} CPUs\n({containers[i]} containers)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('../results/resource_requirements.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: resource_requirements.png")
    plt.close()

def create_workflow_diagram():
    """Workflow của distributed testing"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    ax.text(6, 9.5, 'Distributed Testing Workflow', 
            ha='center', fontsize=14, fontweight='bold')
    
    steps = [
        ("1. Start Infrastructure", "Server + Coordinator containers", 8.5),
        ("2. Calculate Containers", "target_clients / 1000 = N", 7.5),
        ("3. Scale Containers", "docker-compose --scale client-container=N", 6.5),
        ("4. Distribute Clients", "Round-robin across containers", 5.5),
        ("5. Parallel Execution", "Each container runs 1000 clients", 4.5),
        ("6. Collect Results", "Coordinator aggregates metrics", 3.5),
        ("7. Generate Report", "JSON + visualizations", 2.5),
    ]
    
    for i, (title, desc, y) in enumerate(steps):
        # Step box
        color = 'lightgreen' if i == 0 else 'lightblue' if i < 4 else 'lightyellow' if i < 6 else 'lightcoral'
        box = FancyBboxPatch((1, y-0.35), 10, 0.7,
                            boxstyle="round,pad=0.1",
                            edgecolor='black', facecolor=color,
                            linewidth=2)
        ax.add_patch(box)
        
        # Text
        ax.text(1.5, y + 0.15, title, fontsize=11, fontweight='bold', va='center')
        ax.text(1.5, y - 0.15, desc, fontsize=9, style='italic', va='center')
        
        # Arrow to next step
        if i < len(steps) - 1:
            arrow = FancyArrowPatch((6, y - 0.4), (6, y - 0.6),
                                   arrowstyle='->', mutation_scale=20,
                                   color='black', linewidth=2)
            ax.add_patch(arrow)
    
    # Example calculation
    ax.text(6, 1.2, 'Example: 10,000 clients test', 
            ha='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    ax.text(6, 0.8, '10,000 / 1,000 = 10 containers needed', 
            ha='center', fontsize=9)
    ax.text(6, 0.4, 'Each container: 1,000 clients on ports 6000-7000', 
            ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('../results/testing_workflow.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: testing_workflow.png")
    plt.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Generating Scalability Strategy Diagrams")
    print("="*60 + "\n")
    
    create_architecture_diagram()
    create_scaling_comparison()
    create_resource_chart()
    create_workflow_diagram()
    
    print("\n" + "="*60)
    print("✓ All diagrams generated successfully!")
    print("="*60)
    print("\nDiagrams saved to: tests/results/")
    print("  • docker_architecture.png")
    print("  • scaling_comparison.png")
    print("  • resource_requirements.png")
    print("  • testing_workflow.png")
    print()
