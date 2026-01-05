# test_api.py
import requests
import time

API_URL = "http://localhost:8000/search"

# Define the full test suite with expected keywords for validation
TEST_SUITE = [
    {
        "level": "EASY",
        "question": "What is the recommended par level for Captain Morgan at Anderson's Bar?",
        "expected": ["650"]
    },
    {
        "level": "EASY",
        "question": "How many stockout days did Johnson's Bar have in total?",
        "expected": ["12"]
    },
    {
        "level": "MEDIUM",
        "question": "Which Rum has the highest safety stock at Anderson's Bar?",
        "expected": ["Bacardi"]
    },
    {
        "level": "MEDIUM",
        "question": "What is the average fill rate for Brown's Bar?",
        "expected": ["0.95", "95%"]
    },
    {
        "level": "DIFFICULT",
        "question": "Compare the total stockout days between Anderson's Bar and Brown's Bar. Which one is higher?",
        "expected": ["Brown", "21"]
    },
    {
        "level": "DIFFICULT",
        "question": "For Barefoot Wine at Anderson's Bar, is the 7-day forecast higher than the safety stock?",
        "expected": ["No", "lower", "less"]
    },
    {
        "level": "VERY DIFFICULT",
        "question": "Which brand had the absolute lowest fill rate in the 90-day simulation for Anderson's Bar?",
        "expected": ["Malibu", "0.54", "54%"]
    },
    {
        "level": "EDGE CASE",
        "question": "Why does Captain Morgan at Anderson's Bar have a recommended par of 650 even though its next day forecast is 0?",
        "expected": ["safety stock", "avg_daily_ml", "buffer", "average"] 
    }
]

def run_tests():
    print(f"🚀 Starting Validation Suite against {API_URL}...\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(TEST_SUITE, 1):
        print(f"--------------------------------------------------")
        print(f"Test #{i} [{test['level']}]: {test['question']}")
        
        start_time = time.time()
        try:
            response = requests.post(API_URL, json={"query": test['question']})
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                answer = data['result']
                
                # Check PASS/FAIL Logic:
                # Passes if at least one expected keyword is found in the answer
                is_pass = any(k.lower() in answer.lower() for k in test['expected'])
                
                status_icon = "✅ PASS" if is_pass else "❌ FAIL"
                if is_pass: passed += 1
                else: failed += 1
                
                print(f"Status: {status_icon} ({duration:.2f}s)")
                print(f"Answer: {answer.strip()}")
                
                if not is_pass:
                    print(f"⚠️  Expected keywords not found: {test['expected']}")
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                failed += 1
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            failed += 1
            
        print("\n")

    print(f"==================================================")
    print(f"🏁 Final Results: {passed}/{len(TEST_SUITE)} Passed")
    print(f"==================================================")

if __name__ == "__main__":
    run_tests()