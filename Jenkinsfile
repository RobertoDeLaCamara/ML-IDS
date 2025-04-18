pipeline {
    agent any

    environment {
        VENV_DIR = ".venv"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Setup Python') {
            steps {
                sh 'python3 -m venv $VENV_DIR'
                sh '. $VENV_DIR/bin/activate && pip install --upgrade pip'
                sh '. $VENV_DIR/bin/activate && pip install -r src/inference_server/requirements.txt'
            }
        }
        stage('Run Tests') {
            steps {
                sh '. $VENV_DIR/bin/activate && pytest tests/test_inference_server.py --junitxml=test-results.xml'
            }
        }
    }
    post {
        always {
            junit 'test-results.xml'
        }
    }
}
