pipeline {
    agent any
    
    // 环境变量配置
    environment {
        // 项目配置
        PROJECT_NAME = 'ecom-chat-bot'
        
        // Docker 镜像配置
        TEST_IMAGE = 'ecom-chat-bot-test'
        TEST_IMAGE_TAG = "${env.BUILD_NUMBER}"
        
        // 测试环境配置
        TEST_ENV = 'production'
        TEST_BASE_URL = 'http://115.190.75.88:8000'
        
        // 报告目录
        REPORT_DIR = 'backend/tests/reports'
        
        // 通知配置（可选，需要在 Jenkins 中配置 credentials）
        // NOTIFICATION_EMAIL = credentials('notification-email')
        // DINGTALK_WEBHOOK = credentials('dingtalk-webhook')
    }
    
    // 参数化构建
    parameters {
        choice(
            name: 'TEST_LEVEL',
            choices: ['quick', 'full', 'api', 'integration', 'performance', 'security'],
            description: '选择测试级别'
        )
        booleanParam(
            name: 'SKIP_SLOW_TESTS',
            defaultValue: true,
            description: '是否跳过慢速测试'
        )
        booleanParam(
            name: 'RUN_PERFORMANCE_TESTS',
            defaultValue: false,
            description: '是否运行性能测试'
        )
        booleanParam(
            name: 'RUN_SECURITY_TESTS',
            defaultValue: false,
            description: '是否运行安全测试'
        )
        booleanParam(
            name: 'CLEANUP_TEST_DATA',
            defaultValue: true,
            description: '测试后是否清理测试数据'
        )
        booleanParam(
            name: 'REBUILD_IMAGE',
            defaultValue: false,
            description: '是否强制重新构建 Docker 镜像（清理缓存）'
        )
    }
    
    // 构建触发器
    triggers {
        // 定时执行：每天凌晨2点执行完整测试
        cron('0 2 * * *')
        
        // Git推送触发（需要配置webhook）
        // pollSCM('H/5 * * * *')
    }
    
    // 构建选项
    options {
        // 保留最近10次构建
        buildDiscarder(logRotator(numToKeepStr: '10'))
        
        // 超时设置
        timeout(time: 60, unit: 'MINUTES')
        
        // 不允许并发构建
        disableConcurrentBuilds()
        
        // 时间戳
        timestamps()
    }
    
    stages {
        stage('准备环境') {
            steps {
                script {
                    echo "🚀 开始构建 - ${env.BUILD_NUMBER}"
                    echo "📌 Git Branch: ${env.GIT_BRANCH}"
                    echo "📌 Git Commit: ${env.GIT_COMMIT}"
                    echo "📌 测试级别: ${params.TEST_LEVEL}"
                }
                
                // 检出代码
                checkout scm
                
                // 显示项目信息
                sh '''
                    echo "==================================="
                    echo "项目: ${PROJECT_NAME}"
                    echo "测试环境: ${TEST_ENV}"
                    echo "测试服务器: ${TEST_BASE_URL}"
                    echo "Docker 镜像: ${TEST_IMAGE}:${TEST_IMAGE_TAG}"
                    echo "==================================="
                '''
            }
        }
        
        stage('检查环境') {
            steps {
                sh '''
                    echo "=================================="
                    echo "环境检查"
                    echo "=================================="
                    
                    # 检查 Docker
                    echo "检查 Docker..."
                    if docker --version; then
                        echo "✓ Docker 可用"
                    else
                        echo "❌ Docker 未安装"
                        exit 1
                    fi
                    
                    # 检查 Docker Compose
                    echo ""
                    echo "检查 Docker Compose..."
                    if docker-compose --version || docker compose version; then
                        echo "✓ Docker Compose 可用"
                    else
                        echo "⚠️  Docker Compose 不可用（可选）"
                    fi
                    
                    # 检查测试服务器
                    echo ""
                    echo "检查测试服务器..."
                    if curl -s -f ${TEST_BASE_URL}/health >/dev/null 2>&1; then
                        echo "✓ 测试服务器可访问: ${TEST_BASE_URL}"
                    else
                        echo "⚠️  测试服务器暂时不可访问: ${TEST_BASE_URL}"
                    fi
                    
                    echo ""
                    echo "✓ 环境检查完成"
                    echo "=================================="
                '''
            }
        }
        
        stage('构建测试镜像') {
            steps {
                script {
                    echo "🐳 构建 Docker 测试镜像..."
                    
                    def buildArgs = ""
                    if (params.REBUILD_IMAGE) {
                        buildArgs = "--no-cache"
                        echo "强制重新构建镜像（清理缓存）"
                    }
                    
                    sh """
                        # 构建测试镜像
                        docker build ${buildArgs} \
                            -t ${TEST_IMAGE}:${TEST_IMAGE_TAG} \
                            -t ${TEST_IMAGE}:latest \
                            -f .jenkins/Dockerfile \
                            .
                        
                        # 显示镜像信息
                        echo ""
                        echo "镜像构建完成:"
                        docker images ${TEST_IMAGE}
                        
                        echo ""
                        echo "✓ 测试镜像构建完成"
                    """
                }
            }
        }
        
        stage('配置测试环境') {
            steps {
                script {
                    echo "⚙️ 准备测试配置..."
                }
                
                sh '''
                    # 创建报告目录
                    mkdir -p ${WORKSPACE}/${REPORT_DIR}/html
                    mkdir -p ${WORKSPACE}/${REPORT_DIR}/coverage
                    
                    echo "✓ 报告目录已创建"
                '''
            }
        }
        
        stage('运行测试') {
            steps {
                script {
                    echo "🧪 在 Docker 容器中执行测试套件..."
                    
                    // 根据参数选择测试级别
                    def testCommand = ''
                    switch(params.TEST_LEVEL) {
                        case 'quick':
                            testCommand = 'pytest -m "not slow and not performance and not security" --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml'
                            break
                        case 'api':
                            testCommand = 'pytest api/ --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml'
                            break
                        case 'integration':
                            testCommand = 'pytest integration/ --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml'
                            break
                        case 'performance':
                            testCommand = 'pytest -m performance --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml'
                            break
                        case 'security':
                            testCommand = 'pytest -m security --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml'
                            break
                        case 'full':
                        default:
                            testCommand = 'pytest --html=reports/html/report.html --self-contained-html --junitxml=reports/junit.xml --cov=. --cov-report=html:reports/coverage --cov-report=term-missing'
                            break
                    }
                    
                    sh """
                        # 在 Docker 容器中运行测试
                        docker run --rm \
                            -v \${WORKSPACE}:/workspace \
                            -w /workspace/backend/tests \
                            -e TEST_BASE_URL=\${TEST_BASE_URL} \
                            -e TEST_API_PREFIX=/api/v1 \
                            -e TEST_REQUEST_TIMEOUT=30 \
                            -e TEST_LLM_REQUEST_TIMEOUT=60 \
                            -e TEST_CLEANUP_AFTER_TEST=${params.CLEANUP_TEST_DATA} \
                            -e TEST_SKIP_PERFORMANCE=${!params.RUN_PERFORMANCE_TESTS} \
                            -e TEST_SKIP_SECURITY=${!params.RUN_SECURITY_TESTS} \
                            -e TEST_LOG_LEVEL=INFO \
                            -e TEST_TENANT_PREFIX=ci_test_ \
                            -e TEST_MAX_CONCURRENT=10 \
                            ${TEST_IMAGE}:${TEST_IMAGE_TAG} \
                            /bin/bash -c "
                                set -e
                                
                                echo '开始执行测试...'
                                echo '测试级别: ${params.TEST_LEVEL}'
                                echo '测试服务器: \${TEST_BASE_URL}'
                                echo ''
                                
                                # 创建报告目录
                                mkdir -p reports/html reports/coverage
                                
                                # 执行测试
                                ${testCommand} || true
                                
                                echo ''
                                echo '✓ 测试执行完成'
                            "
                        
                        echo "✓ Docker 容器测试完成"
                    """
                }
            }
        }
        
        stage('收集测试报告') {
            steps {
                script {
                    echo "📊 收集测试报告..."
                }
                
                // 发布JUnit测试报告
                junit allowEmptyResults: true, testResults: 'backend/tests/reports/junit.xml'
                
                // 发布HTML报告
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'backend/tests/reports/html',
                    reportFiles: 'report.html',
                    reportName: '测试报告',
                    reportTitles: '自动化测试报告'
                ])
                
                // 发布覆盖率报告（如果存在）
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'backend/tests/reports/coverage',
                    reportFiles: 'index.html',
                    reportName: '覆盖率报告',
                    reportTitles: '代码覆盖率报告'
                ])
                
                // 归档测试报告
                archiveArtifacts artifacts: 'backend/tests/reports/**/*', allowEmptyArchive: true
            }
        }
        
        stage('分析测试结果') {
            steps {
                script {
                    echo "📈 分析测试结果..."
                    
                    // 获取测试统计
                    def testResults = junit 'backend/tests/reports/junit.xml'
                    
                    // 计算测试指标
                    def totalTests = testResults.totalCount
                    def passedTests = testResults.passCount
                    def failedTests = testResults.failCount
                    def skippedTests = testResults.skipCount
                    def passRate = totalTests > 0 ? (passedTests / totalTests * 100).round(2) : 0
                    
                    echo """
                    ========================================
                    测试结果统计:
                    ----------------------------------------
                    总测试数: ${totalTests}
                    通过: ${passedTests}
                    失败: ${failedTests}
                    跳过: ${skippedTests}
                    通过率: ${passRate}%
                    ========================================
                    """
                    
                    // 保存到环境变量供后续使用
                    env.TOTAL_TESTS = totalTests
                    env.PASSED_TESTS = passedTests
                    env.FAILED_TESTS = failedTests
                    env.PASS_RATE = passRate
                    
                    // 判断构建结果
                    if (failedTests > 0) {
                        currentBuild.result = 'UNSTABLE'
                        echo "⚠️ 有测试失败，构建状态设置为 UNSTABLE"
                    }
                    
                    // 如果通过率低于阈值，标记为失败
                    if (passRate < 80) {
                        currentBuild.result = 'FAILURE'
                        error "❌ 测试通过率低于80%，构建失败"
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "🧹 清理环境..."
                
                try {
                    sh '''
                        # 清理 Python 缓存
                        find backend/tests -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
                        find backend/tests -type f -name "*.pyc" -delete 2>/dev/null || true
                        
                        echo "✓ 清理完成"
                    '''
                } catch (Exception e) {
                    echo "清理失败: ${e.message}"
                }
            }
        }
        
        success {
            script {
                echo "✅ 构建成功！"
                
                try {
                    sendNotification('SUCCESS')
                } catch (Exception e) {
                    echo "发送成功通知失败: ${e.message}"
                }
            }
        }
        
        failure {
            script {
                echo "❌ 构建失败！"
                
                try {
                    sendNotification('FAILURE')
                } catch (Exception e) {
                    echo "发送失败通知失败: ${e.message}"
                }
            }
        }
        
        unstable {
            script {
                echo "⚠️ 构建不稳定！"
                
                try {
                    sendNotification('UNSTABLE')
                } catch (Exception e) {
                    echo "发送警告通知失败: ${e.message}"
                }
            }
        }
        
        cleanup {
            script {
                echo "🧹 最终清理..."
                
                // 清理旧的 Docker 镜像
                try {
                    sh '''
                        # 保留最近 3 个测试镜像，删除旧的
                        echo "清理旧的 Docker 镜像..."
                        docker images ${TEST_IMAGE} --format "{{.Tag}}" | \
                            grep -E '^[0-9]+$' | \
                            sort -rn | \
                            tail -n +4 | \
                            xargs -r -I {} docker rmi ${TEST_IMAGE}:{} 2>/dev/null || true
                        
                        # 清理悬空镜像
                        docker image prune -f || true
                        
                        echo "✓ Docker 镜像清理完成"
                    '''
                } catch (Exception e) {
                    echo "清理 Docker 镜像失败: ${e.message}"
                }
            }
        }
    }
}

// 通知函数
def sendNotification(String status) {
    def color = status == 'SUCCESS' ? 'good' : (status == 'UNSTABLE' ? 'warning' : 'danger')
    def emoji = status == 'SUCCESS' ? '✅' : (status == 'UNSTABLE' ? '⚠️' : '❌')
    
    def totalTests = env.TOTAL_TESTS ?: '0'
    def passedTests = env.PASSED_TESTS ?: '0'
    def failedTests = env.FAILED_TESTS ?: '0'
    def passRate = env.PASS_RATE ?: '0'
    
    def message = """
${emoji} 测试构建 ${status}

📋 项目: ${env.PROJECT_NAME}
🔢 构建: #${env.BUILD_NUMBER}
🌿 分支: ${env.GIT_BRANCH ?: 'unknown'}
📊 测试级别: ${params.TEST_LEVEL}

📈 测试统计:
- 总数: ${totalTests}
- 通过: ${passedTests}
- 失败: ${failedTests}
- 通过率: ${passRate}%

🔗 报告: ${env.BUILD_URL}测试报告
⏱️ 耗时: ${currentBuild.durationString}
    """
    
    echo "通知内容:\n${message}"
    
    // 邮件通知（需要配置 credentials 和安装 Email Extension 插件）
    // if (env.NOTIFICATION_EMAIL) {
    //     emailext(
    //         subject: "${emoji} ${env.PROJECT_NAME} - 构建 #${env.BUILD_NUMBER} ${status}",
    //         body: message,
    //         to: env.NOTIFICATION_EMAIL,
    //         recipientProviders: [developers(), requestor()]
    //     )
    // }
    
    // 钉钉通知（需要配置 credentials）
    // if (env.DINGTALK_WEBHOOK) {
    //     sh """
    //         curl -X POST ${env.DINGTALK_WEBHOOK} \
    //         -H 'Content-Type: application/json' \
    //         -d '{
    //             "msgtype": "markdown",
    //             "markdown": {
    //                 "title": "测试构建${status}",
    //                 "text": "${message.replace('"', '\\"').replace('\n', '\\n')}"
    //             }
    //         }'
    //     """
    // }
}
