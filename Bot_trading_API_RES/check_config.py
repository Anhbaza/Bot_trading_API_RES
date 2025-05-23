import os
import yaml

def check_config():
    try:
        # Get current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.yaml')
        
        print(f"Checking config at: {config_path}")
        print(f"Current directory: {current_dir}")
        
        if not os.path.exists(config_path):
            print(f"ERROR: Config file not found at: {config_path}")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        print("\nLoaded config:")
        print("="*50)
        for section, data in config.items():
            print(f"\n{section}:")
            for key, value in data.items():
                # Che giấu giá trị nhạy cảm
                if key in ['token', 'chat_id']:
                    print(f"  {key}: {'*'*len(str(value))}")
                else:
                    print(f"  {key}: {value}")
        print("\n" + "="*50)
        
        # Kiểm tra cấu hình tối thiểu
        if 'telegram' not in config:
            print("\nERROR: Missing 'telegram' section")
        elif 'token' not in config['telegram']:
            print("\nERROR: Missing 'token' in telegram section")
        elif 'chat_id' not in config['telegram']:
            print("\nERROR: Missing 'chat_id' in telegram section")
        else:
            print("\nConfig validation: OK")
            
    except Exception as e:
        print(f"\nError checking config: {str(e)}")

if __name__ == "__main__":
    check_config()
