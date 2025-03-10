pipeline {
    agent {
        label 'pytest'  // Agent label
    }
     environment {
        VENV_DIR = 'venv'  // Virtual environment name
    }
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate && pip install --upgrade pip && pip install -r services/data-collector-service/requirements.txt
                    mkdir -p reports

                     # Ensure src/ is recognized as a Python package
                    mkdir -p src
                    touch src/__init__.py
                    export PYTHONPATH=$(pwd)/src
                '''
            }
        }
        stage('Run Tests') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate && pip install pytest 
                    pytest services/data-collector-service/tests/ --disable-warnings --junitxml=reports/data-collector-service-results.xml
                '''
            }
        }
    }
    post {
        always {
            junit '**/reports/*.xml'
        }
    }
}