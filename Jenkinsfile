pipeline {
    agent any
    
    // 环境变量配置
    environment {
        // 项目配置
        PROJECT_NAME = 'ecom-chat-bot'
        PYTHON_VERSION = '3.11'
        
        // 测试环境配置
        TEST_ENV = 'production'
        TEST_BASE_URL = 'http://115.190.75.88:8000'
        
        // Conda环境
        CONDA_ENV = 'ecom-chat-bot'
        
        // 报告目录
        REPORT_DIR = 'backend/tests/reports'
        
        // 通知配置（根据需要配置）
        NOTIFICATION_EMAIL = credentials('notification-email')
        DINGTALK_WEBHOOK = credentials('dingtalk-webhook')
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
                
                // 清理工作空间（可选）
                // cleanWs()
                
                // 检出代码
                checkout scm
                
                // 显示项目信息
                sh '''
                    echo "==================================="
                    echo "项目: ${PROJECT_NAME}"
                    echo "Python版本: ${PYTHON_VERSION}"
                    echo "测试环境: ${TEST_ENV}"
                    echo "==================================="
                '''
            }
        }
        
        stage('检查环境') {
            steps {
                sh '''
                    # 检查Python和Conda
                    python3 --version || echo "Python3未安装"
                    conda --version || echo "Conda未安装"
                    
                    # 检查测试环境URL
                    curl -s ${TEST_BASE_URL}/health || echo "测试环境不可访问"
                '''
            }
        }
        
        stage('安装依赖') {
            steps {
                script {
                    echo "📦 安装测试依赖..."
                }
                
                sh '''
                    # 激活conda环境（如果不存在则创建）
                    if conda env list | grep -q "^${CONDA_ENV} "; then
                        echo "Conda环境已存在"
                    else
                        echo "创建Conda环境"
                        conda create -n ${CONDA_ENV} python=${PYTHON_VERSION} -y
                    fi
                    
                    # 激活环境并安装依赖
                    source activate ${CONDA_ENV}
                    cd backend/tests
                    pip install -r requirements-test.txt -q
                    
                    echo "✓ 依赖安装完成"
                '''
            }
        }
        
        stage('配置测试环境') {
            steps {
                script {
                    echo "⚙️ 配置测试环境变量..."
                }
                
                sh '''
                    cd backend/tests
                    
                    # 创建测试配置文件
                    cat > .env.test.local << EOF
# Jenkins CI 测试配置
TEST_BASE_URL=${TEST_BASE_URL}
TEST_API_PREFIX=/api/v1

# 超时设置
TEST_REQUEST_TIMEOUT=30
TEST_LLM_REQUEST_TIMEOUT=60

# 测试控制
TEST_CLEANUP_AFTER_TEST=${CLEANUP_TEST_DATA}
TEST_SKIP_PERFORMANCE=${!RUN_PERFORMANCE_TESTS}
TEST_SKIP_SECURITY=${!RUN_SECURITY_TESTS}

# 日志级别
TEST_LOG_LEVEL=INFO

# 测试租户前缀
TEST_TENANT_PREFIX=ci_test_

# 并发设置
TEST_MAX_CONCURRENT=10
EOF
                    
                    echo "✓ 配置文件已创建"
                    cat .env.test.local
                '''
            }
        }
        
        stage('运行测试') {
            steps {
                script {
                    echo "🧪 执行测试套件..."
                    
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
                        source activate ${CONDA_ENV}
                        cd backend/tests
                        
                        # 创建报告目录
                        mkdir -p reports/html reports/coverage
                        
                        # 执行测试
                        ${testCommand} || true
                        
                        echo "✓ 测试执行完成"
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
            }
            
            // 清理临时文件（可选）
            sh '''
                cd backend/tests
                rm -f .env.test.local
            '''
        }
        
        success {
            script {
                echo "✅ 构建成功！"
                
                // 发送成功通知
                sendNotification('SUCCESS')
            }
        }
        
        failure {
            script {
                echo "❌ 构建失败！"
                
                // 发送失败通知
                sendNotification('FAILURE')
            }
        }
        
        unstable {
            script {
                echo "⚠️ 构建不稳定！"
                
                // 发送警告通知
                sendNotification('UNSTABLE')
            }
        }
        
        cleanup {
            // 最终清理
            cleanWs(
                cleanWhenNotBuilt: false,
                deleteDirs: true,
                disableDeferredWipeout: true,
                notFailBuild: true
            )
        }
    }
}

// 通知函数
def sendNotification(String status) {
    def color = status == 'SUCCESS' ? 'good' : (status == 'UNSTABLE' ? 'warning' : 'danger')
    def emoji = status == 'SUCCESS' ? '✅' : (status == 'UNSTABLE' ? '⚠️' : '❌')
    
    def message = """
${emoji} 测试构建 ${status}

📋 项目: ${env.PROJECT_NAME}
🔢 构建: #${env.BUILD_NUMBER}
🌿 分支: ${env.GIT_BRANCH}
📊 测试级别: ${params.TEST_LEVEL}

📈 测试统计:
- 总数: ${env.TOTAL_TESTS}
- 通过: ${env.PASSED_TESTS}
- 失败: ${env.FAILED_TESTS}
- 通过率: ${env.PASS_RATE}%

🔗 报告: ${env.BUILD_URL}测试报告
⏱️ 耗时: ${currentBuild.durationString}
    """
    
    // 邮件通知
    if (env.NOTIFICATION_EMAIL) {
        emailext(
            subject: "${emoji} ${env.PROJECT_NAME} - 构建 #${env.BUILD_NUMBER} ${status}",
            body: message,
            to: env.NOTIFICATION_EMAIL,
            recipientProviders: [developers(), requestor()]
        )
    }
    
    // 钉钉通知
    if (env.DINGTALK_WEBHOOK) {
        sh """
            curl -X POST ${env.DINGTALK_WEBHOOK} \
            -H 'Content-Type: application/json' \
            -d '{
                "msgtype": "markdown",
                "markdown": {
                    "title": "测试构建${status}",
                    "text": "${message.replace('"', '\\"').replace('\n', '\\n')}"
                }
            }'
        """
    }
}
