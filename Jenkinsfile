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
                    . ${VENV_DIR}/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
                    mkdir -p reports
                '''
            }
        }
        stage('Run Tests') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate && pip install pytest 
                    pytest tests/ --disable-warnings --junitxml=reports/results.xml
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