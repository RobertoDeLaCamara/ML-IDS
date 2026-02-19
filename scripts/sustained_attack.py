
import requests
import time
import random

API_URL = "http://localhost:8000/predict"
ATTACK_DURATION = 120  # 2 minutes
REQUEST_INTERVAL = 0.05  # 20 requests per second

def inject_extreme_attack():
    print(f"Starting EXTREME and sustained attack simulation for {ATTACK_DURATION} seconds...")
    start_time = time.time()
    
    # Target IPs
    victims = ["192.168.1.45"]
    
    while time.time() - start_time < ATTACK_DURATION:
        # Create EXTREME values based on feature importance
        payload = {
            "flow_duration": random.randint(5000000, 10000000),
            "tot_fwd_pkts": random.randint(20000, 50000),
            "tot_bwd_pkts": random.randint(20000, 50000),
            "fwd_pkts_s": random.randint(1000000, 5000000),
            "bwd_pkts_s": random.randint(1000000, 5000000),
            "fwd_seg_size_min": 0,  # Highly important feature
            "init_fwd_win_byts": 0, # Empty window is suspicious
            "init_bwd_win_byts": 0,
            "down_up_ratio": random.randint(5, 20),
            "pkt_len_var": random.randint(100000, 500000),
            "syn_flag_cnt": 1,
            "psh_flag_cnt": 1,
            "src_ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "dst_ip": random.choice(victims),
            "dst_port": 80,
            "protocol": 6
        }
        
        try:
            # We don't print every success to avoid flooding terminal
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                pred = response.json().get('prediction')
                if pred and pred[0] != 0:
                    print(f" [CRITICAL] Attack detected from {payload['src_ip']}!")
            else:
                print(f"Failed to inject: {response.status_code}")
        except Exception as e:
            pass
            
        time.sleep(REQUEST_INTERVAL)
    
    print("Extreme sustained attack simulation finished.")

if __name__ == "__main__":
    inject_extreme_attack()
