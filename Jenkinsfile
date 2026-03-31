pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '5'))
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        REGISTRY = "192.168.1.86:5000"
        IMAGE_NAME = "ml-ids"
        NO_PROXY = 'localhost,127.0.0.1,192.168.1.0/24,192.168.1.86,192.168.1.62,192.168.1.45'
        no_proxy = 'localhost,127.0.0.1,192.168.1.0/24,192.168.1.86,192.168.1.62,192.168.1.45'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                echo 'Building Docker image...'
                sh "docker build -f src/inference_server/Dockerfile -t ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} -t ${REGISTRY}/${IMAGE_NAME}:latest ."
            }
        }

        stage('Lint') {
            steps {
                echo 'Running code quality checks...'
                sh """
                docker run --rm \
                    ${REGISTRY}/${IMAGE_NAME}:\${BUILD_NUMBER} \
                    sh -c 'pip install --quiet flake8 && flake8 src/ --max-line-length=120 --count --statistics || true'
                """
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running test suite with coverage...'
                script {
                    try {
                        sh """
                        docker run --name test-mlids-\${BUILD_NUMBER} \
                            -e DATABASE_URL=sqlite+aiosqlite:////app/dist/mlids.db \
                            ${REGISTRY}/${IMAGE_NAME}:\${BUILD_NUMBER} \
                            python -m pytest tests/ -v \
                                --junitxml=test-results.xml \
                                --cov=src \
                                --cov-report=xml:coverage.xml \
                                --cov-report=term-missing \
                                --disable-warnings
                        """
                    } finally {
                        sh "docker cp test-mlids-\${BUILD_NUMBER}:/app/test-results.xml \${WORKSPACE}/test-results.xml || true"
                        sh "docker cp test-mlids-\${BUILD_NUMBER}:/app/coverage.xml \${WORKSPACE}/coverage.xml || true"
                        sh "docker rm test-mlids-\${BUILD_NUMBER} || true"
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                    archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                echo 'Running SonarQube analysis...'
                sh """
                    JENKINS_CONTAINER=\$(cat /proc/self/cgroup | grep -oP '(?<=docker/)[a-f0-9]{64}' | head -1 || hostname)
                    docker run --rm \
                        --volumes-from \${JENKINS_CONTAINER} \
                        -w \${WORKSPACE} \
                        sonarsource/sonar-scanner-cli \
                        -Dsonar.projectKey=ml-ids \
                        -Dsonar.sources=src \
                        -Dsonar.tests=tests \
                        -Dsonar.python.version=3.13 \
                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                        -Dsonar.host.url=http://192.168.1.86:9000 \
                        -Dsonar.login=admin \
                        -Dsonar.password=patilla1 \
                        -Dsonar.scm.disabled=true
                """
            }
        }

        stage('Push to Registry') {
            steps {
                echo "Pushing image to ${REGISTRY}..."
                sh "docker push ${REGISTRY}/${IMAGE_NAME}:\${BUILD_NUMBER}"
                sh "docker push ${REGISTRY}/${IMAGE_NAME}:latest"
            }
        }
    }

    post {
        always {
            sh 'rm -f test-results.xml coverage.xml || true'
            sh "docker rmi ${REGISTRY}/${IMAGE_NAME}:\${BUILD_NUMBER} || true"
        }
        success {
            echo 'Pipeline succeeded!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}
