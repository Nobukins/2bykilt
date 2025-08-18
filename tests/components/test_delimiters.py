#!/usr/bin/env python3
"""
Test different delimiter options for browser arguments
"""

def test_delimiters():
    """Test various delimiter options"""
    
    # Problematic arguments with commas
    args = [
        '--no-sandbox',
        '--disable-setuid-sandbox', 
        '--window-position=50,50',
        '--window-size=1280,720',
        '--single-process'
    ]
    
    print("Original arguments:")
    for arg in args:
        print(f"  {arg}")
    
    print("\nTesting delimiters:")
    
    # Test pipe delimiter
    pipe_joined = '|'.join(args)
    pipe_split = pipe_joined.split('|')
    print(f"Pipe (|): {pipe_split == args} - {'✅' if pipe_split == args else '❌'}")
    
    # Test semicolon delimiter  
    semi_joined = ';'.join(args)
    semi_split = semi_joined.split(';')
    print(f"Semicolon (;): {semi_split == args} - {'✅' if semi_split == args else '❌'}")
    
    # Test newline delimiter
    newline_joined = '\n'.join(args)
    newline_split = newline_joined.split('\n')
    print(f"Newline (\\n): {newline_split == args} - {'✅' if newline_split == args else '❌'}")
    
    # Test space delimiter (might have issues with args containing spaces)
    space_joined = ' '.join(args)
    space_split = space_joined.split(' ')
    print(f"Space ( ): {space_split == args} - {'✅' if space_split == args else '❌'}")
    
    print(f"\nBest option appears to be: pipe (|) or semicolon (;)")
    return '|'  # Return recommended delimiter

if __name__ == "__main__":
    recommended = test_delimiters()
