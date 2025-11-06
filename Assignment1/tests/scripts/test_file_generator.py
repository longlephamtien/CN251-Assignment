"""
Test File Generator for P2P Performance Testing

Generates various sizes of test files to be used for performance evaluation:
- Small files (< 1 MB)
- Medium files (1-10 MB)
- Large files (> 10 MB)
"""

import os
import random
import string
from pathlib import Path

def generate_random_content(size_bytes):
    """Generate random content of specified size"""
    # For better performance, use chunks
    chunk_size = 1024 * 1024  # 1 MB chunks
    content = bytearray()
    
    remaining = size_bytes
    while remaining > 0:
        current_chunk = min(chunk_size, remaining)
        # Mix of random bytes for realistic file size
        chunk = os.urandom(current_chunk)
        content.extend(chunk)
        remaining -= current_chunk
    
    return bytes(content)

def generate_text_file(filepath, size_bytes):
    """Generate a text file with random text"""
    chars = string.ascii_letters + string.digits + ' \n'
    with open(filepath, 'w') as f:
        chars_written = 0
        while chars_written < size_bytes:
            line_length = random.randint(50, 100)
            line = ''.join(random.choices(chars, k=line_length)) + '\n'
            f.write(line)
            chars_written += len(line)
    
    # Truncate to exact size
    with open(filepath, 'r+') as f:
        f.seek(size_bytes)
        f.truncate()

def generate_binary_file(filepath, size_bytes):
    """Generate a binary file with random data"""
    with open(filepath, 'wb') as f:
        content = generate_random_content(size_bytes)
        f.write(content)

def generate_test_files(output_dir, file_configs):
    """
    Generate test files based on configurations
    
    Args:
        output_dir: Directory to save files
        file_configs: List of tuples (filename, size_bytes, file_type)
                     file_type: 'text' or 'binary'
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {len(file_configs)} test files in {output_dir}...")
    
    for filename, size_bytes, file_type in file_configs:
        filepath = output_path / filename
        
        if file_type == 'text':
            generate_text_file(str(filepath), size_bytes)
        else:
            generate_binary_file(str(filepath), size_bytes)
        
        actual_size = os.path.getsize(filepath)
        print(f"  ✓ {filename}: {actual_size:,} bytes ({file_type})")
    
    print(f"✓ All test files generated in {output_dir}")
    return True

def generate_default_test_files(output_dir='../files'):
    """Generate default set of test files for performance testing"""
    
    KB = 1024
    MB = 1024 * KB
    
    file_configs = [
        # Small files (< 1 MB)
        ('small_text_10kb.txt', 10 * KB, 'text'),
        ('small_binary_50kb.bin', 50 * KB, 'binary'),
        ('small_text_100kb.txt', 100 * KB, 'text'),
        ('small_binary_500kb.bin', 500 * KB, 'binary'),
        ('small_text_800kb.txt', 800 * KB, 'text'),
        
        # Medium files (1-10 MB)
        ('medium_text_1mb.txt', 1 * MB, 'text'),
        ('medium_binary_2mb.bin', 2 * MB, 'binary'),
        ('medium_text_5mb.txt', 5 * MB, 'text'),
        ('medium_binary_8mb.bin', 8 * MB, 'binary'),
        ('medium_text_10mb.txt', 10 * MB, 'text'),
        
        # Large files (> 10 MB)
        ('large_binary_15mb.bin', 15 * MB, 'binary'),
        ('large_text_20mb.txt', 20 * MB, 'text'),
        ('large_binary_50mb.bin', 50 * MB, 'binary'),
        ('large_text_100mb.txt', 100 * MB, 'text'),
        ('large_binary_200mb.bin', 200 * MB, 'binary'),
    ]
    
    return generate_test_files(output_dir, file_configs)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        # Default to files directory
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'files'
    
    print("=== P2P Test File Generator ===")
    generate_default_test_files(str(output_dir))
    print("\n✓ Test files ready for performance evaluation")
