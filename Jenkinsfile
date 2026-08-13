pipeline {
    agent any

    parameters {
        choice(name: 'ENV', choices: ['test', 'prod'], description: '部署环境（必须选择）')
        booleanParam(name: 'DEPLOY_FRONTEND', defaultValue: false, description: '是否部署前端（上传 OSS）')
        booleanParam(name: 'REBUILD_BACKEND', defaultValue: false, description: '是否重新构建后端镜像并推送')
        string(name: 'BACKEND_VERSION', defaultValue: 'latest', description: '后端镜像版本/Tag（默认 latest）')
        booleanParam(name: 'DEPLOY_BACKEND', defaultValue: false, description: '是否部署后端（K8s）')
    }

    environment {
        NAMESPACE = "${params.ENV == 'prod' ? 'mb-pr' : 'mb-test'}"
        DOMAIN = "${params.ENV == 'prod' ? 'pomelo.youbanban.com' : 'pomelo.dev.youbanban.com'}"
        OSS_BUCKET = "${params.ENV == 'prod' ? 'pomelo-mb-prod' : 'pomelo-mb-test'}"
        OSS_IP = "${params.ENV == 'prod' ? '106.14.228.188' : '47.102.237.237'}"
        TOOLS = '/mnt/devops-tools'
        KUBECONFIG = '/mnt/kubeconf/config'
    }

    stages {
        stage('Env Setup') {
            steps {
                sh """#!/bin/bash
                    APPHOME=${TOOLS}
                    . ${TOOLS}/env.sh
                    echo "Environment: ${params.ENV}"
                    echo "Namespace: ${NAMESPACE}"
                    echo "Domain: ${DOMAIN}"
                    echo "OSS Bucket: ${OSS_BUCKET}"
                    echo "Registry: \$DOCKER_REG_BASE_URL/\$DOCKER_NS"

                    if [ -x /mnt/ossutil ]; then
                        cp /mnt/ossutil ./ossutil && chmod +x ./ossutil
                        echo "ossutil ready"
                    else
                        echo "WARN: /mnt/ossutil not found, OSS steps will fail"
                    fi

                    if [ -x ./ossutil ]; then
                        export OSS_ACCESS_KEY_ID=\$(\$KUBECTL get secret pomelo-secrets -n ${NAMESPACE} -o jsonpath='{.data.OSS_ACCESS_KEY_ID}' | base64 -d)
                        export OSS_ACCESS_KEY_SECRET=\$(\$KUBECTL get secret pomelo-secrets -n ${NAMESPACE} -o jsonpath='{.data.OSS_ACCESS_KEY_SECRET}' | base64 -d)
                        export OSS_ENDPOINT=oss-cn-shanghai-internal.aliyuncs.com
                        ./ossutil config -e \$OSS_ENDPOINT -i \$OSS_ACCESS_KEY_ID -k \$OSS_ACCESS_KEY_SECRET -L CH 2>&1 || true
                        echo "ossutil configured"
                    fi
                """
            }
        }

        stage('Frontend: Upload to OSS') {
            when { expression { params.DEPLOY_FRONTEND } }
            steps {
                sh """#!/bin/bash
                    if [ ! -x ./ossutil ]; then
                        echo "ERROR: ossutil not available"
                        exit 1
                    fi
                    echo "window.POMELO_API_BASE = \\"https://${DOMAIN}/api\\";" > frontend/.output/public/config.js
                    ./ossutil cp -r frontend/.output/public/ oss://${OSS_BUCKET}/ --update
                    echo "Frontend deployed to oss://${OSS_BUCKET}/"
                """
            }
        }

        stage('Backend: Build & Push') {
            when { expression { params.REBUILD_BACKEND } }
            steps {
                script {
                    def backendTag = params.BACKEND_VERSION?.trim() ?: 'latest'
                    sh """#!/bin/bash
                        APPHOME=${TOOLS}
                        . ${TOOLS}/env.sh
                        echo "\$DOCKER_REG_PASSWORD" | docker login \$DOCKER_REG_BASE_URL -u \$DOCKER_REG_USER --password-stdin

                        echo "Building ${backendTag} ..."
                        docker pull docker.m.daocloud.io/library/python:3.13-slim
                        docker tag docker.m.daocloud.io/library/python:3.13-slim python:3.13-slim
                        cd backend
                        docker build -t pomelo-backend:${backendTag} .

                        echo "Pushing to ACR ..."
                        docker tag pomelo-backend:${backendTag} \$DOCKER_REG_BASE_URL/\$DOCKER_NS/pomelo-backend:${backendTag}
                        docker push \$DOCKER_REG_BASE_URL/\$DOCKER_NS/pomelo-backend:${backendTag}
                        docker tag pomelo-backend:${backendTag} registry-vpc.cn-shanghai.aliyuncs.com/ybbmb/pomelo-backend:${backendTag}
                        docker push registry-vpc.cn-shanghai.aliyuncs.com/ybbmb/pomelo-backend:${backendTag}
                        echo "Done: pomelo-backend:${backendTag}"
                    """
                    env.BACKEND_TAG = backendTag
                }
            }
        }

        stage('Backend: Deploy to K8s') {
            when { expression { params.DEPLOY_BACKEND } }
            steps {
                script {
                    def backendTag = env.BACKEND_TAG ?: params.BACKEND_VERSION?.trim() ?: 'latest'
                    sh """#!/bin/bash
                        APPHOME=${TOOLS}
                        . ${TOOLS}/env.sh

                        TMPDIR=\$(mktemp -d)
                        for f in deploy/k8s/namespace.yaml deploy/k8s/certificate.yaml deploy/k8s/pv-nas.yaml deploy/k8s/oss-webui.yaml deploy/k8s/oss-webui-plugin.yaml deploy/k8s/backend/service.yaml deploy/k8s/backend/deployment.yaml deploy/k8s/ingress.yaml; do
                            name=\$(basename \$f)
                            sed -e 's/<TAG>/${backendTag}/g' \\
                                -e 's/<NAMESPACE>/${NAMESPACE}/g' \\
                                -e 's/<DOMAIN>/${DOMAIN}/g' \\
                                -e 's/<OSS_BUCKET>/${OSS_BUCKET}/g' \\
                                -e 's/<OSS_IP>/${OSS_IP}/g' \\
                                "\$f" > "\$TMPDIR/\$name"
                            echo "  apply \$name"
                            \$KUBECTL apply -f "\$TMPDIR/\$name"
                        done
                        rm -rf "\$TMPDIR"

                        echo "Deploy complete. Checking backend rollout..."
                        \$KUBECTL rollout status deployment/pomelo-backend -n ${NAMESPACE} --timeout=120s || true
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded: ${params.ENV}, frontend=${params.DEPLOY_FRONTEND}, rebuild=${params.REBUILD_BACKEND}, deploy=${params.DEPLOY_BACKEND}"
        }
        failure {
            echo "Pipeline FAILED: ${params.ENV}"
        }
    }
}
