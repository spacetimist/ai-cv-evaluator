#!/usr/bin/env python3
"""
Quick Test Script - Test API Endpoints

This script tests the basic functionality of the CV Evaluator API.
Usage: python scripts/test_api.py
"""

import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_health_check():
    """Test health check endpoint"""
    print_section("Testing Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        
        data = response.json()
        print("✓ Health check passed")
        print(f"  Status: {data['status']}")
        print(f"  LLM Provider: {data['llm_provider']}")
        print(f"  LLM Model: {data['llm_model']}")
        return True
    
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_upload(cv_path=None, project_path=None):
    """Test document upload endpoint"""
    print_section("Testing Document Upload")
    
    # If no files provided, use dummy files
    if not cv_path or not project_path:
        print("⚠ No PDF files provided. Skipping upload test.")
        print("  To test upload, run: python scripts/test_api.py <cv.pdf> <project.pdf>")
        return None, None
    
    try:
        with open(cv_path, 'rb') as cv_file, \
             open(project_path, 'rb') as project_file:
            
            files = {
                'cv': ('cv.pdf', cv_file, 'application/pdf'),
                'project_report': ('project.pdf', project_file, 'application/pdf')
            }
            
            response = requests.post(f"{BASE_URL}/api/v1/upload", files=files)
            response.raise_for_status()
            
            data = response.json()
            cv_id = data['cv']['id']
            project_id = data['project_report']['id']
            
            print("✓ Upload successful")
            print(f"  CV ID: {cv_id}")
            print(f"  Project ID: {project_id}")
            
            return cv_id, project_id
    
    except FileNotFoundError:
        print(f"✗ File not found: {cv_path} or {project_path}")
        return None, None
    
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        return None, None


def test_evaluate(cv_id, project_id, job_title="Backend Engineer"):
    """Test evaluation endpoint"""
    print_section("Testing Evaluation")
    
    if not cv_id or not project_id:
        print("⚠ Skipping evaluation test (no document IDs)")
        return None
    
    try:
        payload = {
            "cv_id": cv_id,
            "project_report_id": project_id,
            "job_title": job_title
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/evaluate",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        job_id = data['id']
        
        print("✓ Evaluation queued")
        print(f"  Job ID: {job_id}")
        print(f"  Status: {data['status']}")
        
        return job_id
    
    except Exception as e:
        print(f"✗ Evaluation failed: {e}")
        return None


def test_result(job_id, max_wait=120):
    """Test result endpoint and poll until completion"""
    print_section("Testing Result Retrieval")
    
    if not job_id:
        print("⚠ Skipping result test (no job ID)")
        return None
    
    try:
        print(f"Polling for results (max {max_wait}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(f"{BASE_URL}/api/v1/result/{job_id}")
            response.raise_for_status()
            
            data = response.json()
            status = data['status']
            
            print(f"  [{int(time.time() - start_time)}s] Status: {status}", end='\r')
            
            if status == 'completed':
                print("\n✓ Evaluation completed!")
                result = data['result']
                
                print("\n--- RESULTS ---")
                print(f"CV Match Rate: {result['cv_match_rate']}")
                print(f"CV Feedback: {result['cv_feedback'][:100]}...")
                print(f"\nProject Score: {result['project_score']}/5")
                print(f"Project Feedback: {result['project_feedback'][:100]}...")
                print(f"\nOverall Summary:")
                print(f"{result['overall_summary'][:200]}...")
                
                return result
            
            elif status == 'failed':
                print(f"\n✗ Evaluation failed")
                print(f"  Error: {data.get('error_message', 'Unknown error')}")
                return None
            
            time.sleep(2)
        
        print(f"\n⚠ Timeout after {max_wait}s (status: {status})")
        return None
    
    except Exception as e:
        print(f"\n✗ Result retrieval failed: {e}")
        return None


def test_list_jobs():
    """Test listing evaluation jobs"""
    print_section("Testing Job Listing")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/results?limit=5")
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✓ Job listing successful")
        print(f"  Total jobs: {data['total']}")
        print(f"  Showing: {len(data['jobs'])} jobs")
        
        if data['jobs']:
            print("\n  Recent jobs:")
            for job in data['jobs'][:3]:
                print(f"    - {job['id'][:8]}... | {job['status']} | {job['job_title']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Job listing failed: {e}")
        return False


def test_stats():
    """Test statistics endpoint"""
    print_section("Testing Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/stats")
        response.raise_for_status()
        
        data = response.json()
        
        print("✓ Statistics retrieved")
        print(f"  Total jobs: {data['total_jobs']}")
        print(f"  Queued: {data['queued']}")
        print(f"  Processing: {data['processing']}")
        print(f"  Completed: {data['completed']}")
        print(f"  Failed: {data['failed']}")
        
        if data['completed'] > 0:
            print(f"  Avg CV match: {data['average_cv_match_rate']}")
            print(f"  Avg project score: {data['average_project_score']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Statistics failed: {e}")
        return False


def main():
    """Main test runner"""
    print("\n" + "🚀 CV Evaluator API Test Script")
    
    # Check if files were provided
    cv_path = sys.argv[1] if len(sys.argv) > 1 else None
    project_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run tests
    tests_passed = 0
    tests_total = 6
    
    # Test 1: Health check
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Upload
    cv_id, project_id = test_upload(cv_path, project_path)
    if cv_id and project_id:
        tests_passed += 1
    
    # Test 3: Evaluate
    job_id = test_evaluate(cv_id, project_id) if cv_id else None
    if job_id:
        tests_passed += 1
    
    # Test 4: Result
    result = test_result(job_id) if job_id else None
    if result:
        tests_passed += 1
    
    # Test 5: List jobs
    if test_list_jobs():
        tests_passed += 1
    
    # Test 6: Stats
    if test_stats():
        tests_passed += 1
    
    # Summary
    print_section("Test Summary")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if cv_path and project_path:
        print("\n✓ Full integration test completed")
    else:
        print("\n⚠ Partial test (no PDF files provided)")
        print("  Run with: python scripts/test_api.py <cv.pdf> <project.pdf>")
    
    print("\n" + "="*60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)