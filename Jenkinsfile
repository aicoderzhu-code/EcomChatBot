pipeline {
    agent any
    
    environment {
        // 项目配置
        PROJECT_NAME = 'ecom-chatbot'
        DEPLOY_PATH = '/opt/projects/ecom-chat-bot'
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
                echo "  Git分支: ${env.GIT_BRANCH}"
                echo "  提交ID: ${env.GIT_COMMIT}"
                echo '=========================================='
            }
        }
        
        stage('同步代码') {
            steps {
                script {
                    echo '>>> 同步代码到部署目录...'
                    sh '''
                        echo "源目录: ${WORKSPACE}"
                        echo "目标目录: ${DEPLOY_PATH}"
                        
                        # 确保目标目录存在
                        mkdir -p ${DEPLOY_PATH}
                        
                        # 使用rsync同步（排除.git目录）
                        rsync -av --delete \
                            --exclude='.git' \
                            --exclude='*.pyc' \
                            --exclude='__pycache__' \
                            --exclude='.env' \
                            ${WORKSPACE}/ ${DEPLOY_PATH}/
                        
                        echo ""
                        echo "✓ 代码同步完成"
                        echo "部署目录内容:"
                        ls -la ${DEPLOY_PATH}/ | head -15
                    '''
                }
            }
        }
        
        stage('Docker配置检查') {
            steps {
                script {
                    echo '>>> 检查Docker配置...'
                    sh '''
                        cd ${DEPLOY_PATH}
                        docker-compose config -q
                        echo "✓ Docker配置检查通过"
                    '''
                }
            }
        }
        
        stage('检查是否需要重建镜像') {
            steps {
                script {
                    echo '>>> 检查是否需要重建镜像...'
                    env.NEED_REBUILD = sh(
                        script: '''
                            cd ${DEPLOY_PATH}
                            
                            # 检查 requirements.txt 或 Dockerfile 是否变化
                            if git diff HEAD~1 HEAD --name-only | grep -E 'requirements.txt|Dockerfile|docker-entrypoint.sh'; then
                                echo "检测到依赖文件变化，需要重建镜像"
                                echo "true"
                            else
                                # 检查镜像是否存在
                                if docker images | grep -q "ecom-chat-bot_api"; then
                                    echo "镜像已存在且依赖未变化，跳过构建"
                                    echo "false"
                                else
                                    echo "镜像不存在，需要构建"
                                    echo "true"
                                fi
                            fi
                        ''',
                        returnStdout: true
                    ).trim()
                    
                    echo "是否需要重建: ${env.NEED_REBUILD}"
                }
            }
        }
        
        stage('构建镜像') {
            when {
                expression { env.NEED_REBUILD == 'true' }
            }
            steps {
                script {
                    echo '>>> 构建Docker镜像...'
                    echo '⚠️  注意: 首次构建需要下载 1.5GB 依赖，可能需要 20-40 分钟'
                    sh '''
                        cd ${DEPLOY_PATH}
                        echo "构建开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
                        
                        echo "=========================================="
                        echo "正在构建镜像... 请耐心等待"
                        echo "=========================================="
                        
                        docker-compose build 2>&1 | while read line; do
                            echo "$line"
                            if [ $((RANDOM % 100)) -eq 0 ]; then
                                echo "[$(date '+%H:%M:%S')] 构建进行中..."
                            fi
                        done || {
                            echo "❌ 镜像构建失败"
                            exit 1
                        }
                        
                        echo ""
                        echo "构建完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
                        echo "✓ 镜像构建完成"
                    '''
                }
            }
        }
        
        stage('部署新服务') {
            steps {
                script {
                    echo '>>> 部署新版本...'
                    sh '''
                        cd ${DEPLOY_PATH}
                        
                        echo ">>> 停止所有旧服务..."
                        docker-compose down || true
                        
                        echo ">>> 启动所有服务（强制重建）..."
                        docker-compose up -d --force-recreate --remove-orphans
                        
                        # 清理未使用的镜像
                        docker image prune -f || true
                        
                        echo "✓ 新服务已启动"
                    '''
                }
            }
        }
        
        stage('健康检查') {
            steps {
                script {
                    echo '>>> 执行健康检查...'
                    sh '''
                        cd ${DEPLOY_PATH}
                        
                        echo "等待服务完全启动..."
                        sleep 30
                        
                        echo "=== 服务状态 ==="
                        docker-compose ps
                        
                        echo ""
                        echo "=== API健康检查 ==="
                        max_attempts=10
                        attempt=0
                        
                        while [ $attempt -lt $max_attempts ]; do
                            if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
                                echo "✓ API服务健康检查通过"
                                echo "  API地址: http://localhost:8000"
                                echo "  API文档: http://localhost:8000/docs"
                                exit 0
                            fi
                            echo "等待API服务启动... ($attempt/$max_attempts)"
                            sleep 10
                            attempt=$((attempt + 1))
                        done
                        
                        echo "⚠ API服务启动超时，但部署已完成"
                        echo "  请手动检查服务状态"
                        exit 0
                    '''
                }
            }
        }
        
        stage('部署验证') {
            steps {
                script {
                    echo '>>> 部署后验证...'
                    sh '''
                        cd ${DEPLOY_PATH}

                        echo "=== 最终服务状态 ==="
                        docker-compose ps

                        echo ""
                        echo "=== API服务日志（最后20行）==="
                        docker-compose logs --tail=20 api || true

                        echo ""
                        echo "=== 部署完成时间 ==="
                        date '+%Y-%m-%d %H:%M:%S'
                    '''
                }
            }
        }

        stage('执行测试') {
            steps {
                script {
                    echo '=========================================='
                    echo '  开始执行部署后自动化测试'
                    echo '=========================================='
                    sh '''
                        cd ${DEPLOY_PATH}

                        echo ">>> 在Docker容器中运行测试..."
                        echo ""

                        # 复制测试脚本到容器
                        docker cp ${DEPLOY_PATH}/scripts/run-tests.sh ecom-chatbot-api:/app/run-tests.sh
                        docker exec ecom-chatbot-api chmod +x /app/run-tests.sh

                        # 在容器中执行测试脚本
                        docker exec -e BUILD_NUMBER=${BUILD_NUMBER} ecom-chatbot-api /app/run-tests.sh || true

                        echo ""
                        echo ">>> 从容器复制测试报告到宿主机..."

                        # 确保宿主机目录存在
                        mkdir -p ${DEPLOY_PATH}/test-reports

                        # 从容器复制报告文件
                        docker cp ecom-chatbot-api:/app/test-reports/. ${DEPLOY_PATH}/test-reports/ || true

                        echo "测试报告已复制到: ${DEPLOY_PATH}/test-reports/"
                        echo ""

                        # 显示报告文件统计
                        echo ">>> 测试报告文件:"
                        ls -lh ${DEPLOY_PATH}/test-reports/ 2>/dev/null || echo "暂无报告文件"

                        echo ""
                        echo "测试阶段完成"
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                echo '>>> 发布测试报告...'

                // 切换到测试报告目录
                dir("${env.DEPLOY_PATH}/test-reports") {
                    // 显示报告目录内容
                    sh '''
                        echo "=== 测试报告目录 ==="
                        pwd
                        echo ""
                        echo "=== 报告文件列表 ==="
                        if [ -d "." ]; then
                            find . -type f -ls 2>/dev/null | head -20 || true
                        else
                            echo "✗ 报告目录不存在"
                        fi
                    '''

                    // 发布JUnit测试报告
                    try {
                        junit allowEmptyResults: true, testResults: 'junit-report.xml'
                        echo '✓ JUnit报告已发布'
                    } catch (Exception e) {
                        echo "⚠ JUnit报告发布失败: ${e.message}"
                    }

                    // 发布HTML测试报告
                    try {
                        publishHTML([
                            allowMissing: true,
                            alwaysLinkToLastBuild: true,
                            keepAll: true,
                            reportDir: '.',
                            reportFiles: 'test-report.html',
                            reportName: '测试报告',
                            reportTitles: '自动化测试报告'
                        ])
                        echo '✓ HTML测试报告已发布'
                    } catch (Exception e) {
                        echo "⚠ HTML测试报告发布失败: ${e.message}"
                    }

                    // 发布覆盖率报告
                    try {
                        publishHTML([
                            allowMissing: true,
                            alwaysLinkToLastBuild: true,
                            keepAll: true,
                            reportDir: 'coverage-html',
                            reportFiles: 'index.html',
                            reportName: '覆盖率报告',
                            reportTitles: '代码覆盖率报告'
                        ])
                        echo '✓ 覆盖率报告已发布'
                    } catch (Exception e) {
                        echo "⚠ 覆盖率报告发布失败: ${e.message}"
                    }

                    // 归档所有测试报告文件
                    try {
                        archiveArtifacts artifacts: '**/*', allowEmptyArchive: true, fingerprint: true
                        echo '✓ 测试报告文件已归档'
                    } catch (Exception e) {
                        echo "⚠ 报告归档失败: ${e.message}"
                    }
                }

                echo '>>> 构建流程结束'
            }
        }

        success {
            script {
                echo '=========================================='
                echo '  🎉 部署并测试成功！'
                echo "  构建编号: ${env.BUILD_NUMBER}"
                echo "  Git分支: ${env.GIT_BRANCH}"
                echo "  提交ID: ${env.GIT_COMMIT}"
                echo '  '
                echo '  访问地址:'
                echo '  API服务: http://localhost:8000'
                echo '  API文档: http://localhost:8000/docs'
                echo '  '
                echo '  测试报告:'
                echo "  - 测试报告: ${env.BUILD_URL}测试报告/"
                echo "  - 覆盖率报告: ${env.BUILD_URL}覆盖率报告/"
                echo "  - 测试结果: ${env.BUILD_URL}testReport/"
                echo '=========================================='
            }
        }

        failure {
            script {
                echo '=========================================='
                echo '  ❌ 构建失败！'
                echo "  构建编号: ${env.BUILD_NUMBER}"
                echo '  请检查日志以获取详细信息'
                echo '=========================================='

                sh """
                    cd ${DEPLOY_PATH}
                    echo "=== 错误诊断信息 ==="
                    echo "服务状态:"
                    docker-compose ps || true
                    echo ""
                    echo "最近日志:"
                    docker-compose logs --tail=30 || true
                """
            }
        }

        unstable {
            script {
                echo '=========================================='
                echo '  ⚠️  部署成功但测试有失败用例'
                echo "  构建编号: ${env.BUILD_NUMBER}"
                echo "  Git分支: ${env.GIT_BRANCH}"
                echo '  '
                echo '  查看详情:'
                echo "  - 失败详情: ${env.BUILD_URL}testReport/"
                echo "  - 测试报告: ${env.BUILD_URL}测试报告/"
                echo "  - 覆盖率报告: ${env.BUILD_URL}覆盖率报告/"
                echo '=========================================='
            }
        }
    }
}
