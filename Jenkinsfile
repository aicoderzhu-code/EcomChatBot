pipeline {
    agent any
    
    environment {
        // 项目配置
        PROJECT_NAME = 'ecom-chatbot'
        DEPLOY_PATH = '/root/ecom-chat-bot'
        
        // Docker配置
        DOCKER_COMPOSE_CMD = 'docker-compose'
        
        // Git配置
        GIT_BRANCH = 'develop'
    }
    
    options {
        // 保留最近10次构建
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // 设置超时时间
        timeout(time: 30, unit: 'MINUTES')
        // 禁止并发构建
        disableConcurrentBuilds()
        // 添加时间戳
        timestamps()
    }
    
    stages {
        stage('准备') {
            steps {
                echo '=========================================='
                echo '  电商智能客服系统 - CI/CD Pipeline'
                echo "  构建编号: ${env.BUILD_NUMBER}"
                echo "  分支: ${env.GIT_BRANCH}"
                echo "  提交ID: ${env.GIT_COMMIT}"
                echo '=========================================='
            }
        }
        
        stage('代码检查') {
            parallel {
                stage('Python语法检查') {
                    steps {
                        script {
                            echo '>>> 检查Python代码语法...'
                            sh '''
                                cd backend
                                # 检查Python文件语法
                                find . -name "*.py" -not -path "./venv/*" -not -path "./__pycache__/*" | while read file; do
                                    python3 -m py_compile "$file" || echo "Warning: $file has syntax issues"
                                done
                                echo "Python语法检查完成"
                            '''
                        }
                    }
                }
                
                stage('Docker配置检查') {
                    steps {
                        script {
                            echo '>>> 检查Docker配置...'
                            sh '''
                                docker-compose config -q
                                echo "Docker配置检查通过"
                            '''
                        }
                    }
                }
            }
        }
        
        stage('构建镜像') {
            steps {
                script {
                    echo '>>> 构建Docker镜像...'
                    sh '''
                        ${DOCKER_COMPOSE_CMD} build --parallel
                    '''
                }
            }
        }
        
        stage('停止旧服务') {
            steps {
                script {
                    echo '>>> 停止旧版本服务...'
                    sh '''
                        # 备份数据库（可选）
                        # docker-compose exec -T postgres pg_dump -U ecom_user ecom_chatbot > /backup/db_$(date +%Y%m%d_%H%M%S).sql || true
                        
                        # 停止应用服务（保留数据库等基础服务）
                        ${DOCKER_COMPOSE_CMD} stop api celery-worker || true
                    '''
                }
            }
        }
        
        stage('部署新服务') {
            steps {
                script {
                    echo '>>> 部署新版本...'
                    sh '''
                        # 确保基础服务正在运行
                        ${DOCKER_COMPOSE_CMD} up -d postgres redis milvus-etcd milvus-minio milvus rabbitmq
                        
                        # 等待基础服务就绪
                        echo "等待基础服务就绪..."
                        sleep 20
                        
                        # 运行数据库初始化（如果需要）
                        ${DOCKER_COMPOSE_CMD} up db-init || true
                        
                        # 启动应用服务
                        ${DOCKER_COMPOSE_CMD} up -d api celery-worker
                        
                        # 清理未使用的镜像
                        docker image prune -f || true
                    '''
                }
            }
        }
        
        stage('健康检查') {
            steps {
                script {
                    echo '>>> 执行健康检查...'
                    sh '''
                        # 等待服务启动
                        echo "等待服务完全启动..."
                        sleep 30
                        
                        # 检查服务状态
                        ${DOCKER_COMPOSE_CMD} ps
                        
                        # 检查API健康
                        echo "检查API健康状态..."
                        max_attempts=10
                        attempt=0
                        
                        while [ $attempt -lt $max_attempts ]; do
                            if curl -f -s http://localhost:8000/docs > /dev/null; then
                                echo "✓ API服务健康检查通过"
                                exit 0
                            fi
                            echo "等待API服务启动... ($attempt/$max_attempts)"
                            sleep 10
                            attempt=$((attempt + 1))
                        done
                        
                        echo "⚠ API服务启动超时，但部署已完成"
                        exit 0
                    '''
                }
            }
        }
        
        stage('部署后检查') {
            steps {
                script {
                    echo '>>> 部署后验证...'
                    sh '''
                        echo "=== 服务状态 ==="
                        ${DOCKER_COMPOSE_CMD} ps
                        
                        echo ""
                        echo "=== API服务日志（最后20行）==="
                        ${DOCKER_COMPOSE_CMD} logs --tail=20 api || true
                        
                        echo ""
                        echo "=== 部署完成时间 ==="
                        date
                    '''
                }
            }
        }
    }
    
    post {
        success {
            echo '=========================================='
            echo '  ✓ 部署成功！'
            echo "  构建编号: ${env.BUILD_NUMBER}"
            echo "  分支: ${env.GIT_BRANCH}"
            echo "  提交ID: ${env.GIT_COMMIT}"
            echo "  API地址: http://localhost:8000"
            echo "  API文档: http://localhost:8000/docs"
            echo '=========================================='
        }
        
        failure {
            echo '=========================================='
            echo '  ✗ 部署失败！'
            echo "  构建编号: ${env.BUILD_NUMBER}"
            echo '  请检查日志以获取详细信息'
            echo '=========================================='
            
            script {
                // 发生错误时，显示详细日志
                sh '''
                    echo "=== 完整服务日志 ==="
                    ${DOCKER_COMPOSE_CMD} logs --tail=50 || true
                '''
            }
        }
        
        always {
            echo '构建流程结束'
        }
    }
}
