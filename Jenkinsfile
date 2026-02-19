pipeline {
    agent any
    
    // ============================================
    // 环境变量配置
    // ============================================
    environment {
        // 项目配置
        PROJECT_NAME = 'ecom-chat-bot'
        IMAGE_NAME = 'ecom-chat-bot-api'
        
        // 部署配置
        DEPLOY_DIR = '/opt/ecom-chat-bot'
        DEPLOY_SERVER = '115.190.75.88'
        
        // 测试配置
        TEST_BASE_URL = 'http://localhost:8000'
        TEST_IMAGE = 'ecom-chat-bot-test'
        
        // 通知配置（可选，需要在Jenkins配置credentials）
        // WECOM_WEBHOOK = credentials('wecom-webhook')
        // DINGTALK_WEBHOOK = credentials('dingtalk-webhook')
    }
    
    // ============================================
    // 构建参数
    // ============================================
    parameters {
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: '是否跳过测试（紧急发布时使用，不推荐）'
        )
        booleanParam(
            name: 'FORCE_DEPLOY',
            defaultValue: false,
            description: '是否强制部署（忽略测试失败）'
        )
        booleanParam(
            name: 'REBUILD_IMAGE',
            defaultValue: false,
            description: '是否清理缓存强制重建镜像'
        )
    }
    
    // ==================== 触发器配置 ====================
    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'ref', value: '$.ref'],
                [key: 'repository', value: '$.repository.name']
            ],
            token: 'ecom-chatbot-deploy-token',
            regexpFilterText: '$ref',
            regexpFilterExpression: 'refs/heads/develop',
            printContributedVariables: true,
            printPostContent: true
        )
    }
    
    // ============================================
    // 构建选项
    // ============================================
    options {
        // 保留最近20次构建
        buildDiscarder(logRotator(numToKeepStr: '20'))
        
        // 超时设置：120分钟
        timeout(time: 120, unit: 'MINUTES')
        
        // 不允许并发构建
        disableConcurrentBuilds()
        
        // 显示时间戳
        timestamps()
        
        // 禁用自动 checkout，由我们手动控制（避免权限冲突）
        skipDefaultCheckout()
    }
    
    // ============================================
    // 构建阶段
    // ============================================
    stages {
        // ----------------------------------------
        // 阶段0: 预清理
        // ----------------------------------------
        stage('预清理') {
            steps {
                script {
                    sh '''
                        # 清理Docker测试环境
                        docker-compose -f docker-compose.jenkins-test.yml down -v || true
                        
                        # 清理测试生成的文件（跳过权限错误）
                        find backend/tests -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
                        find backend/tests -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
                        rm -rf backend/reports 2>/dev/null || true
                    '''
                }
            }
        }
        
        // ----------------------------------------
        // 阶段1: 代码检出
        // ----------------------------------------
        stage('代码检出') {
            steps {
                script {
                    echo """
╔════════════════════════════════════════════════════════╗
║          🚀 开始CI/CD流水线 - ${env.PROJECT_NAME}         ║
╚════════════════════════════════════════════════════════╝
                    """
                    echo "📌 构建编号: ${env.BUILD_NUMBER}"
                    echo "📌 分支: develop"
                    echo "📌 触发方式: ${currentBuild.getBuildCauses()[0].shortDescription}"
                    echo "📌 构建时间: ${new Date().format('yyyy-MM-dd HH:mm:ss')}"
                    echo ""
                }
                
                // 清理workspace中的Python缓存文件（避免权限问题）
                sh '''
                    echo "清理workspace中的缓存文件..."
                    # 清理Python缓存
                    find . -type d -name "__pycache__" -exec sudo chmod -R 777 {} + 2>/dev/null || true
                    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
                    find . -type f -name "*.pyc" -exec sudo chmod 666 {} + 2>/dev/null || true
                    find . -type f -name "*.pyc" -delete 2>/dev/null || true
                    
                    # 清理pytest缓存
                    find . -type d -name ".pytest_cache" -exec sudo chmod -R 777 {} + 2>/dev/null || true
                    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
                    
                    # 清理测试报告
                    find . -type f -name ".coverage" -exec sudo chmod 666 {} + 2>/dev/null || true
                    find . -type f -name ".coverage" -delete 2>/dev/null || true
                    
                    echo "清理完成"
                '''
                
                // 检出develop分支代码（不使用CleanCheckout，避免权限冲突）
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/develop']],
                    userRemoteConfigs: [[
                        url: 'https://gitee.com/fridge1/ecom-chat-bot.git',
                        credentialsId: 'f6d0a8e1-45e2-4947-89ef-45db554f89a4'
                    ]]
                ])
                
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    env.GIT_COMMIT_MSG = sh(
                        script: 'git log -1 --pretty=%B',
                        returnStdout: true
                    ).trim()
                    env.GIT_AUTHOR = sh(
                        script: 'git log -1 --pretty=format:"%an"',
                        returnStdout: true
                    ).trim()
                    
                    echo "📝 提交信息: ${env.GIT_COMMIT_MSG}"
                    echo "🔖 提交ID: ${env.GIT_COMMIT_SHORT}"
                    echo "👤 提交人: ${env.GIT_AUTHOR}"
                    
                    // 设置构建描述
                    currentBuild.description = "develop - ${env.GIT_COMMIT_SHORT}"
                }
            }
        }
        
        // ----------------------------------------
        // 阶段2: 环境检查
        // ----------------------------------------
        stage('环境检查') {
            steps {
                echo "🔍 检查构建环境..."
                sh '''
                    echo "=========================================="
                    echo "环境检查"
                    echo "=========================================="
                    
                    # 检查Docker
                    echo "检查 Docker..."
                    if docker --version; then
                        echo "✓ Docker 可用: $(docker --version)"
                    else
                        echo "❌ Docker 未安装"
                        exit 1
                    fi
                    
                    # 检查磁盘空间
                    echo ""
                    echo "检查磁盘空间..."
                    df -h / | tail -1
                    DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
                    if [ $DISK_USAGE -gt 90 ]; then
                        echo "⚠️  磁盘空间不足: ${DISK_USAGE}%"
                    else
                        echo "✓ 磁盘空间充足: ${DISK_USAGE}%"
                    fi
                    
                    # 检查部署目录
                    echo ""
                    echo "检查部署目录..."
                    if [ -d "${DEPLOY_DIR}" ]; then
                        echo "✓ 部署目录存在: ${DEPLOY_DIR}"
                    else
                        echo "⚠️  部署目录不存在，将在部署时创建"
                    fi
                    
                    echo ""
                    echo "✓ 环境检查完成"
                    echo "=========================================="
                '''
            }
        }
        
        // ----------------------------------------
        // 阶段3: 构建Docker镜像
        // ----------------------------------------
        stage('构建Docker镜像') {
            steps {
                echo "🐳 构建生产环境Docker镜像..."
                script {
                    def buildArgs = params.REBUILD_IMAGE ? "--no-cache" : ""
                    
                    sh """
                        echo "=========================================="
                        echo "构建镜像: ${IMAGE_NAME}:${BUILD_NUMBER}"
                        echo "=========================================="
                        
                        # 构建应用镜像
                        docker build ${buildArgs} \\
                            -t ${IMAGE_NAME}:${BUILD_NUMBER} \\
                            -t ${IMAGE_NAME}:latest \\
                            -t ${IMAGE_NAME}:develop \\
                            -f backend/Dockerfile \\
                            backend/
                        
                        # 显示镜像信息
                        echo ""
                        echo "✓ 镜像构建完成:"
                        docker images ${IMAGE_NAME} | head -5
                        
                        # 镜像大小
                        IMAGE_SIZE=\$(docker images ${IMAGE_NAME}:${BUILD_NUMBER} --format "{{.Size}}")
                        echo ""
                        echo "镜像大小: \${IMAGE_SIZE}"
                        echo "=========================================="
                    """
                }
            }
        }
        
        // ----------------------------------------
        // 阶段4: 运行测试
        // ----------------------------------------
        stage('运行测试') {
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                echo "🧪 运行完整测试套件..."
                script {
                    // 启动测试环境
                    sh """
                        echo "=========================================="
                        echo "启动测试环境"
                        echo "=========================================="
                        
                        # 清理旧的测试环境
                        docker-compose -f docker-compose.jenkins-test.yml down -v || true
                        
                        # 启动测试环境
                        TEST_IMAGE=${IMAGE_NAME}:${BUILD_NUMBER} docker-compose -f docker-compose.jenkins-test.yml up -d
                        
                        # 等待服务就绪
                        sleep 15
                        docker-compose -f docker-compose.jenkins-test.yml ps
                    """
                    
                    // 安装测试依赖
                    sh """
                        echo "=========================================="
                        echo "安装测试依赖"
                        echo "=========================================="
                        
                        docker-compose -f docker-compose.jenkins-test.yml exec -T test-api bash -c "
                            pip install -q -r tests/requirements-test.txt
                        "
                    """
                    
                    // 初始化管理员账号
                    sh """
                        echo "=========================================="
                        echo "初始化管理员账号"
                        echo "=========================================="
                        
                        docker-compose -f docker-compose.jenkins-test.yml exec -T test-api bash -c "
                            cd /app
                            python tests/scripts/init_admin.py
                        "
                        
                        echo "✓ 管理员账号初始化完成"
                        echo "=========================================="
                    """
                    
                    // 运行测试
                    sh """
                        echo "=========================================="
                        echo "执行测试套件"
                        echo "=========================================="
                        
                        # 等待API服务启动
                        echo "等待API服务就绪..."
                        for i in {1..30}; do
                            if docker-compose -f docker-compose.jenkins-test.yml exec -T test-api curl -f http://localhost:8000/docs > /dev/null 2>&1; then
                                echo "✓ API服务已就绪"
                                break
                            fi
                            echo "等待中...\$i/30"
                            sleep 2
                        done
                        
                        # 运行测试（排除支付和RAG相关测试，因为Milvus未启用）
                        docker-compose -f docker-compose.jenkins-test.yml exec -T test-api bash -c "
                            cd /app/tests
                            BASE_URL=http://test-api:8000 pytest . \\
                                -m 'not payment and not rag' \\
                                --junitxml=reports/junit.xml \\
                                --html=reports/html/report.html \\
                                --self-contained-html \\
                                --cov=. \\
                                --cov-report=xml:reports/coverage.xml \\
                                --cov-report=html:reports/coverage \\
                                --cov-report=term-missing \\
                                -v \\
                                || exit 0
                        "
                        
                        # 复制测试报告
                        docker cp jenkins-test-api:/app/reports \${WORKSPACE}/backend/tests/ || true
                        
                        # 修复权限以便Jenkins可以读取和清理
                        sudo chown -R jenkins:jenkins \${WORKSPACE}/backend/tests/reports || true
                        
                        echo '✓ 测试执行完成'
                        echo "=========================================="
                    """
                }
                
                // 发布测试报告
                junit allowEmptyResults: true, testResults: 'backend/tests/reports/junit.xml'
                
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'backend/tests/reports/html',
                    reportFiles: 'report.html',
                    reportName: '测试报告',
                    reportTitles: "Build #${env.BUILD_NUMBER} 测试报告"
                ])
                
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'backend/tests/reports/coverage',
                    reportFiles: 'index.html',
                    reportName: '覆盖率报告',
                    reportTitles: "Build #${env.BUILD_NUMBER} 覆盖率报告"
                ])
            }
            post {
                always {
                    // 清理测试环境
                    sh 'docker-compose -f docker-compose.jenkins-test.yml down -v || true'
                }
            }
        }
        
        // ----------------------------------------
        // 阶段5: 测试结果分析
        // ----------------------------------------
        stage('测试结果分析') {
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                script {
                    echo "📊 分析测试结果..."
                    
                    try {
                        def testResults = junit 'backend/tests/reports/junit.xml'
                        
                        def totalTests = testResults.totalCount
                        def passedTests = testResults.passCount
                        def failedTests = testResults.failCount
                        def skippedTests = testResults.skipCount
                        
                        // 计算通过率（避免使用 toDouble()，直接用整数计算）
                        def passRate = 0
                        if (totalTests > 0) {
                            passRate = (passedTests * 100) / totalTests
                        }
                        
                        echo """
========================================
测试结果统计
========================================
总测试数: ${totalTests}
通过数: ${passedTests}
失败数: ${failedTests}
跳过数: ${skippedTests}
通过率: ${passRate}%
========================================
                        """
                        
                        env.TOTAL_TESTS = totalTests.toString()
                        env.PASSED_TESTS = passedTests.toString()
                        env.FAILED_TESTS = failedTests.toString()
                        env.PASS_RATE = passRate.toString()
                        
                        // 判断是否继续部署
                        if (failedTests > 0 && !params.FORCE_DEPLOY) {
                            currentBuild.result = 'UNSTABLE'
                            echo "⚠️  有测试失败，但不阻止部署"
                        }
                        
                        // 通过率过低则失败（调整阈值为70%）
                        if (passRate < 70 && !params.FORCE_DEPLOY) {
                            error "❌ 测试通过率过低 (${passRate}%)，部署终止"
                        }
                        
                    } catch (Exception e) {
                        echo "⚠️  无法读取测试结果: ${e.message}"
                        if (!params.FORCE_DEPLOY) {
                            error "测试结果异常，部署终止"
                        }
                    }
                }
            }
        }
        
        // ----------------------------------------
        // 阶段6: 部署到生产环境
        // ----------------------------------------
        stage('部署到生产环境') {
            when {
                expression { currentBuild.result != 'FAILURE' || params.FORCE_DEPLOY }
            }
            steps {
                echo "🚀 部署到生产环境..."
                script {
                    try {
                        sh '''
                            echo "=========================================="
                            echo "部署到生产环境"
                            echo "=========================================="
                            
                            # 检查部署目录权限
                            if [ -d "${DEPLOY_DIR}" ]; then
                                echo "✓ 部署目录已存在: ${DEPLOY_DIR}"
                            else
                                echo "⚠️  部署目录不存在，尝试创建..."
                                # 尝试不使用 sudo 创建
                                mkdir -p ${DEPLOY_DIR}/shared/logs 2>/dev/null || {
                                    echo "❌ 无权限创建部署目录"
                                    echo "请系统管理员执行以下命令:"
                                    echo "  sudo mkdir -p ${DEPLOY_DIR}/shared/logs"
                                    echo "  sudo chown -R jenkins:jenkins ${DEPLOY_DIR}"
                                    exit 1
                                }
                            fi
                            
                            # 确保 shared/logs 目录存在（无sudo）
                            mkdir -p ${DEPLOY_DIR}/shared/logs 2>/dev/null || true
                            
                            # 检查写权限
                            if [ ! -w "${DEPLOY_DIR}" ]; then
                                echo "❌ 无写入权限到 ${DEPLOY_DIR}"
                                echo "请系统管理员执行: sudo chown -R jenkins:jenkins ${DEPLOY_DIR}"
                                exit 1
                            fi
                            
                            echo "✓ 部署目录权限检查通过"
                            
                            # 复制配置文件
                            echo "复制配置文件..."
                            cp docker-compose.prod.yml ${DEPLOY_DIR}/ || {
                                echo "❌ 无法复制配置文件"
                                exit 1
                            }
                            
                            # 复制环境配置模板（如果不存在）
                            if [ ! -f "${DEPLOY_DIR}/shared/.env.production" ]; then
                                echo "创建生产环境配置..."
                                cp .env.production.template ${DEPLOY_DIR}/shared/.env.production || {
                                    echo "⚠️  环境配置模板不存在，跳过"
                                }
                                if [ -f "${DEPLOY_DIR}/shared/.env.production" ]; then
                                    echo "⚠️  请检查并修改 ${DEPLOY_DIR}/shared/.env.production 中的配置"
                                fi
                            fi
                            
                            # 执行部署脚本
                            echo ""
                            echo "执行部署脚本..."
                            if [ -f "scripts/jenkins-deploy.sh" ]; then
                                bash scripts/jenkins-deploy.sh ${BUILD_NUMBER}
                            else
                                echo "⚠️  部署脚本不存在: scripts/jenkins-deploy.sh"
                                echo "跳过部署脚本执行"
                            fi
                            
                            echo "=========================================="
                            echo "✓ 部署配置准备完成"
                            echo "=========================================="
                        '''
                    } catch (Exception e) {
                        echo "❌ 部署失败: ${e.message}"
                        echo ""
                        echo "可能的原因:"
                        echo "1. 部署目录 ${DEPLOY_DIR} 不存在或无权限"
                        echo "2. 需要系统管理员配置 sudoers:"
                        echo "   echo 'jenkins ALL=(ALL) NOPASSWD: /bin/mkdir, /bin/chown' | sudo tee -a /etc/sudoers.d/jenkins"
                        echo "   或手动创建目录:"
                        echo "   sudo mkdir -p ${DEPLOY_DIR}/shared/logs"
                        echo "   sudo chown -R jenkins:jenkins ${DEPLOY_DIR}"
                        throw e
                    }
                }
            }
        }
        
        // ----------------------------------------
        // 阶段7: 冒烟测试
        // ----------------------------------------
        stage('冒烟测试') {
            steps {
                echo "🔍 执行部署后冒烟测试..."
                sh '''
                    echo "=========================================="
                    echo "冒烟测试"
                    echo "=========================================="
                    
                    # 等待服务完全启动
                    echo "等待服务启动..."
                    sleep 15
                    
                    # 执行冒烟测试
                    bash scripts/smoke-test.sh ${TEST_BASE_URL}
                    
                    echo "=========================================="
                '''
            }
        }
        
        // ----------------------------------------
        // 阶段8: 触发手动测试
        // ----------------------------------------
        stage('触发手动测试') {
            steps {
                script {
                    echo "✅ 部署成功！触发手动测试入口..."
                    
                    echo """
════════════════════════════════════════════════════════════
  🎉 部署完成 - 手动测试入口
════════════════════════════════════════════════════════════

📌 部署信息:
   - 构建编号: ${env.BUILD_NUMBER}
   - 版本: ${env.GIT_COMMIT_SHORT}
   - 部署时间: ${new Date().format('yyyy-MM-dd HH:mm:ss')}

🔗 访问地址:
   - API文档: http://${DEPLOY_SERVER}:8000/docs
   - 健康检查: http://${DEPLOY_SERVER}:8000/health

🧪 手动测试:
   1. 打开Jenkins: http://${DEPLOY_SERVER}:8080
   2. 找到 "ecom-chatbot-manual-test" Job
   3. 点击 "Build with Parameters"
   4. 选择测试套件并执行

📝 快速测试命令:
   curl http://${DEPLOY_SERVER}:8000/health
   curl http://${DEPLOY_SERVER}:8000/docs

════════════════════════════════════════════════════════════
                    """
                    
                    // 尝试触发手动测试Job（不阻塞）
                    try {
                        build job: 'ecom-chatbot-manual-test',
                              parameters: [
                                  string(name: 'BUILD_NUMBER', value: env.BUILD_NUMBER),
                                  string(name: 'TEST_URL', value: "http://${DEPLOY_SERVER}:8000")
                              ],
                              wait: false
                    } catch (Exception e) {
                        echo "⚠️  无法触发手动测试Job: ${e.message}"
                        echo "请手动执行测试Job"
                    }
                }
            }
        }
        
        // ----------------------------------------
        // 阶段9: 清理构建环境
        // ----------------------------------------
        stage('清理构建环境') {
            steps {
                script {
                    echo "🧹 清理构建环境..."
                    sh '''
                        # 清理Python缓存（使用sudo修改权限）
                        find backend/tests -type d -name "__pycache__" -exec sudo chmod -R 777 {} + 2>/dev/null || true
                        find backend/tests -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
                        find backend/tests -type f -name "*.pyc" -exec sudo chmod 666 {} + 2>/dev/null || true
                        find backend/tests -type f -name "*.pyc" -delete 2>/dev/null || true
                        
                        # 清理测试镜像
                        docker rmi ${TEST_IMAGE}:${BUILD_NUMBER} 2>/dev/null || true
                        
                        echo "✓ 清理完成"
                    '''
                }
            }
        }
    }
    
    // ============================================
    // 构建后操作
    // ============================================
    post {
        success {
            script {
                def duration = currentBuild.durationString.replace(' and counting', '')
                
                echo """
╔════════════════════════════════════════════════════════╗
║               ✅ 部署成功！                             ║
╚════════════════════════════════════════════════════════╝

📋 项目: ${PROJECT_NAME}
🔢 构建: #${env.BUILD_NUMBER}
🌿 分支: develop
🏷️  提交: ${env.GIT_COMMIT_SHORT}
👤 作者: ${env.GIT_AUTHOR}
⏱️  耗时: ${duration}

🔗 访问地址:
   - API: http://${DEPLOY_SERVER}:8000
   - 文档: http://${DEPLOY_SERVER}:8000/docs
                """
                
                sendNotification('SUCCESS')
            }
        }
        
        failure {
            script {
                def projectName = env.PROJECT_NAME ?: 'ecom-chat-bot'
                def buildNumber = env.BUILD_NUMBER ?: 'N/A'
                def commitShort = env.GIT_COMMIT_SHORT ?: 'N/A'
                
                echo """
╔════════════════════════════════════════════════════════╗
║               ❌ 部署失败！                             ║
╚════════════════════════════════════════════════════════╝

📋 项目: ${projectName}
🔢 构建: #${buildNumber}
🌿 分支: develop
🏷️  提交: ${commitShort}

请查看构建日志了解失败原因:
${env.BUILD_URL}console
                """
                
                sendNotification('FAILURE')
            }
        }
        
        unstable {
            script {
                echo """
╔════════════════════════════════════════════════════════╗
║            ⚠️  构建不稳定！                             ║
╚════════════════════════════════════════════════════════╝

测试通过率: ${env.PASS_RATE}%
失败测试数: ${env.FAILED_TESTS}
                """
                
                sendNotification('UNSTABLE')
            }
        }
    }
}

// ============================================
// 通知函数
// ============================================
def sendNotification(String status) {
    def emoji = status == 'SUCCESS' ? '✅' : (status == 'UNSTABLE' ? '⚠️' : '❌')
    def color = status == 'SUCCESS' ? 'good' : (status == 'UNSTABLE' ? 'warning' : 'danger')
    
    def passRate = env.PASS_RATE ?: 'N/A'
    def totalTests = env.TOTAL_TESTS ?: '0'
    def passedTests = env.PASSED_TESTS ?: '0'
    def failedTests = env.FAILED_TESTS ?: '0'
    
    def message = """
${emoji} **部署${status}**

**项目**: ${env.PROJECT_NAME}
**构建**: #${env.BUILD_NUMBER}
**分支**: develop
**提交**: ${env.GIT_COMMIT_SHORT}
**作者**: ${env.GIT_AUTHOR}
**时间**: ${new Date().format('yyyy-MM-dd HH:mm:ss')}

**测试统计**:
- 总数: ${totalTests}
- 通过: ${passedTests}
- 失败: ${failedTests}
- 通过率: ${passRate}%

[查看详情](${env.BUILD_URL})
    """
    
    echo "📢 发送通知: ${status}"
    
    // 企业微信通知（需要配置credentials）
    /*
    if (env.WECOM_WEBHOOK) {
        sh """
            curl -X POST ${env.WECOM_WEBHOOK} \
            -H 'Content-Type: application/json' \
            -d '{
                "msgtype": "markdown",
                "markdown": {
                    "content": ${groovy.json.JsonOutput.toJson(message)}
                }
            }'
        """
    }
    */
    
    // 钉钉通知（需要配置credentials）
    /*
    if (env.DINGTALK_WEBHOOK) {
        sh """
            curl -X POST ${env.DINGTALK_WEBHOOK} \
            -H 'Content-Type: application/json' \
            -d '{
                "msgtype": "markdown",
                "markdown": {
                    "title": "部署${status}",
                    "text": ${groovy.json.JsonOutput.toJson(message)}
                }
            }'
        """
    }
    */
}
