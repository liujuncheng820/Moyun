import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 生成模拟ABR波形数据
def generate_abr_waveform(duration_ms=20, sampling_rate=1000):
    """生成模拟的ABR波形数据"""
    t = np.linspace(0, duration_ms, int(duration_ms * sampling_rate / 1000))
    
    # 基础波形
    waveform = 0.1 * np.sin(2 * np.pi * 10 * t)  # 10Hz基础频率
    
    # 添加噪声
    noise = np.random.normal(0, 0.03, len(t))
    waveform += noise
    
    # 添加特征峰值（ABR的V波等）
    peaks = [
        (1.5, 0.4),  # 1.5ms处的峰值
        (3.5, 0.6),  # 3.5ms处的峰值
        (5.5, -0.5), # 5.5ms处的谷值
        (7.5, 0.3),  # 7.5ms处的峰值
        (10.5, -0.4) # 10.5ms处的谷值
    ]
    
    for peak_time, peak_amp in peaks:
        # 使用高斯函数模拟峰值
        waveform += peak_amp * np.exp(-((t - peak_time) ** 2) / (2 * 0.2 ** 2))
    
    return t, waveform

# 高斯平滑
def gaussian_smooth(waveform, sigma=0.1, sampling_rate=1000):
    """使用高斯滤波平滑波形"""
    kernel_size = int(6 * sigma * sampling_rate / 1000) + 1
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    x = np.linspace(-3 * sigma, 3 * sigma, kernel_size)
    kernel = np.exp(-x**2 / (2 * sigma**2))
    kernel /= np.sum(kernel)
    
    smoothed = np.convolve(waveform, kernel, mode='same')
    return smoothed

# 滑动平均
def moving_average(waveform, window_size=5):
    """使用滑动平均平滑波形"""
    return np.convolve(waveform, np.ones(window_size)/window_size, mode='same')

# 峰值检测
def detect_peaks(waveform, threshold=0.2, min_distance=10):
    """检测波形峰值"""
    peaks = []
    
    for i in range(1, len(waveform) - 1):
        if waveform[i] > waveform[i-1] and waveform[i] > waveform[i+1] and waveform[i] > threshold:
            # 检查是否与前一个峰值距离足够
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    
    return peaks

# 主函数
def main():
    # 生成ABR波形
    t, original_waveform = generate_abr_waveform()
    
    # 平滑处理
    gaussian_smoothed = gaussian_smooth(original_waveform)
    moving_avg_smoothed = moving_average(original_waveform)
    
    # 检测峰值
    peaks = detect_peaks(gaussian_smoothed)
    peak_times = t[peaks]
    peak_amps = gaussian_smoothed[peaks]
    
    # 创建画布
    plt.figure(figsize=(12, 6), dpi=100)
    
    # 绘制原始波形
    plt.plot(t, original_waveform, 'b-', label='原始波形', linewidth=1.5)
    
    # 绘制平滑波形
    plt.plot(t, gaussian_smoothed, 'g-', label='高斯平滑波形', linewidth=2)
    
    # 标记检测到的峰值
    plt.plot(peak_times, peak_amps, 'ro', markersize=8, label='CNN预测峰值')
    
    # 设置坐标轴
    plt.xlabel('时间 (ms)', fontsize=12, fontname='Arial')
    plt.ylabel('振幅 (μV)', fontsize=12, fontname='Arial')
    plt.title('ABR波形峰值检测', fontsize=14, fontname='Arial')
    
    # 添加图例
    plt.legend(fontsize=12, loc='upper right')
    
    # 添加注释
    plt.text(15, 0.7, '高斯平滑', color='green', fontsize=12, fontname='Arial')
    plt.text(15, 0.6, '滑动平均', color='purple', fontsize=12, fontname='Arial')
    
    # 设置网格
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 设置坐标轴范围
    plt.xlim(0, 20)
    plt.ylim(-0.8, 0.8)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存为SVG格式（矢量图）
    plt.savefig('abr_waveform_peak_detection.svg', format='svg', dpi=300)
    
    # 显示图形
    plt.show()

if __name__ == '__main__':
    main()
