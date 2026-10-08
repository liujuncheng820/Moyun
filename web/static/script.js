// 中文VibeWriting - 基于DeepSeek Reasoner的智能小说生成器
// Socket.IO 连接和聊天功能实现

// 全局变量
let socket;
let isConnected = false;
let isGenerating = false;

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    setupEventListeners();
    updateConnectionStatus();
});

// 初始化Socket.IO连接
function initializeSocket() {
    socket = io();
    
    // 连接成功
    socket.on('connect', function() {
        console.log('已连接到服务器');
        isConnected = true;
        updateConnectionStatus();
    });
    
    // 连接断开
    socket.on('disconnect', function() {
        console.log('与服务器断开连接');
        isConnected = false;
        updateConnectionStatus();
    });
    
    // 接收DeepSeek Reasoner回复
    socket.on('ai_response', function(data) {
        console.log('收到DeepSeek Reasoner回复:', data);
        addMessage('assistant', data.message);
        hideLoading();
        isGenerating = false;
        updateSendButton();
    });
    
    // 接收小说内容
    socket.on('novel_content', function(data) {
        console.log('收到小说内容:', data);
        if (data.content) {
            updateNovelContent(data.content);
        }
        if (data.isComplete) {
            hideLoading();
            isGenerating = false;
            updateSendButton();
            addMessage('assistant', '小说生成完成！您可以在左侧查看完整内容。');
        }
    });
    
    // 接收错误消息
    socket.on('error_message', function(data) {
        console.log('收到错误消息:', data);
        addMessage('assistant', '抱歉，生成过程中出现了错误：' + data.error);
        hideLoading();
        isGenerating = false;
        updateSendButton();
    });
}

// 设置事件监听器
function setupEventListeners() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    // 发送按钮点击事件
    sendBtn.addEventListener('click', sendMessage);
    
    // 输入框回车事件
    chatInput.addEventListener('keydown', handleKeyDown);
}

// 处理键盘事件
function handleKeyDown(event) {
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
}

// 发送消息
function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message || !isConnected || isGenerating) {
        return;
    }
    
    // 添加用户消息到聊天界面
    addMessage('user', message);
    
    // 清空输入框
    chatInput.value = '';
    
    // 显示加载动画
    showLoading();
    isGenerating = true;
    updateSendButton();
    
    // 发送消息到服务器
    socket.emit('user_message', {
        message: message,
        timestamp: new Date().toISOString()
    });
}

// 添加消息到聊天界面
function addMessage(type, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const currentTime = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-content">
                <p>${escapeHtml(content)}</p>
                <span class="message-time">${currentTime}</span>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <p>${escapeHtml(content)}</p>
                <span class="message-time">${currentTime}</span>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 更新小说内容显示
function updateNovelContent(content) {
    const novelContent = document.getElementById('novelContent');
    const welcomeMessage = novelContent.querySelector('.welcome-message');
    const novelContentWrapper = document.getElementById('novelContentWrapper');
    const novelTextContent = document.getElementById('novelTextContent');
    
    // 隐藏欢迎消息，显示小说内容区域
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    if (novelContentWrapper) {
        novelContentWrapper.style.display = 'block';
    }
    
    // 配置marked选项
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (err) {}
            }
            return hljs.highlightAuto(code).value;
        }
    });
    
    // 渲染markdown内容
    const renderedContent = marked.parse(content);
    
    // 更新小说内容
    if (novelTextContent) {
        novelTextContent.innerHTML = renderedContent;
        
        // 更新字数统计
        const wordCount = content.replace(/[^\u4e00-\u9fa5]/g, '').length;
        const wordCountElement = document.getElementById('wordCount');
        if (wordCountElement) {
            wordCountElement.textContent = `${wordCount} 字`;
        }
        
        // 更新生成时间
        const generationTimeElement = document.getElementById('generationTime');
        if (generationTimeElement) {
            const now = new Date();
            generationTimeElement.textContent = `生成于 ${now.toLocaleString()}`;
        }
        
        // 提取并设置标题
        const titleMatch = content.match(/^#\s+(.+)$/m);
        const novelTitleElement = document.getElementById('novelTitle');
        if (titleMatch && novelTitleElement) {
            novelTitleElement.textContent = titleMatch[1];
        } else if (novelTitleElement) {
            novelTitleElement.textContent = '智能生成小说';
        }
    }
    
    // 滚动到顶部以显示标题
    novelContent.scrollTop = 0;
}

// 显示加载动画
function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
}

// 隐藏加载动画
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'none';
}

// 更新连接状态
function updateConnectionStatus() {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = statusIndicator.nextElementSibling;
    
    if (isConnected) {
        statusIndicator.className = 'status-indicator online';
        statusText.textContent = '在线';
    } else {
        statusIndicator.className = 'status-indicator offline';
        statusText.textContent = '离线';
    }
}

// 更新发送按钮状态
function updateSendButton() {
    const sendBtn = document.getElementById('sendBtn');
    const chatInput = document.getElementById('chatInput');
    
    if (isGenerating || !isConnected) {
        sendBtn.disabled = true;
        chatInput.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    } else {
        sendBtn.disabled = false;
        chatInput.disabled = false;
        sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    }
}

// 发送示例提示
function sendExample(element) {
    const chatInput = document.getElementById('chatInput');
    chatInput.value = element.textContent;
    sendMessage();
}

// 清空内容
function clearContent() {
    const novelContent = document.getElementById('novelContent');
    const novelText = novelContent.querySelector('.novel-text');
    const welcomeMessage = novelContent.querySelector('.welcome-message');
    
    if (novelText) {
        novelText.remove();
    }
    
    if (welcomeMessage) {
        welcomeMessage.style.display = 'block';
    }
}

// 保存小说
function saveNovel() {
    const novelText = document.querySelector('.novel-text');
    if (!novelText) {
        alert('没有内容可以保存！');
        return;
    }
    
    const content = Array.from(novelText.querySelectorAll('p'))
        .map(p => p.textContent)
        .join('\n\n');
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `小说_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 错误处理
window.addEventListener('error', function(event) {
    console.error('JavaScript错误:', event.error);
});

// Socket.IO错误处理
socket?.on('connect_error', function(error) {
    console.error('Socket.IO连接错误:', error);
    isConnected = false;
    updateConnectionStatus();
});