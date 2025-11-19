import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np

def plot_layer_arrangement(shelf_width, layer_items_df):
    """
    绘制货架排列线段图
    
    参数:
    shelf_width: 货架宽度（毫米）
    df: DataFrame，包含以下列:
        - item_code: 商品编号
        - position: 商品左端点位置（毫米）
        - width: 单个商品宽度（毫米）
        - facing: 连续摆放数量
        - segment_rank: 货物属性
    
    返回:
    matplotlib图形对象
    """
    # 创建图形和坐标轴
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # 设置y轴位置（所有商品在同一水平线上）
    y_position = 0.5
    
    # 绘制货架基线
    ax.axhline(y=y_position, color='black', linewidth=2, label='货架基线')
    
    # 绘制货架边界
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.7, label='货架左边界')
    ax.axvline(x=shelf_width, color='gray', linestyle='--', alpha=0.7, label='货架右边界')
    
    # 遍历DataFrame中的每个商品组
    for idx, row in layer_items_df.iterrows():
        # 计算整个商品组的总宽度
        total_width = row['item_width'] * row['facing']
        right_position = row['position'] + total_width
        
        # 根据facing值选择颜色
        color = 'red' if row['facing'] >= 2 else 'blue'
        linewidth = 3 if row['facing'] >= 2 else 2
        
        # 绘制整个商品组的线段
        ax.plot([row['position'], right_position], 
                [y_position, y_position], 
                color=color, linewidth=linewidth)
        
        # 为每个单独的商品绘制分界点
        for i in range(1, row['facing']):
            # 计算分界点位置
            divider_x = row['position'] + i * row['item_width']
            
            # 绘制分界点（垂直线段）
            ax.plot([divider_x, divider_x], 
                    [y_position - 0.05, y_position + 0.05], 
                    color='black', linewidth=2)
        
        # 计算文本位置（整个商品组的中点）
        text_x = row['position'] + total_width / 2
        text_y = y_position + 0.08  # 稍微上移避免重叠
        
        # 添加商品信息标注
        label = f"{row['item_code']}\n(segment_rank:{row['segment_rank']})"
        if row['facing'] > 1:
            label += f"\n×{row['facing']}"
            
        ax.text(text_x, text_y, 
                label, 
                ha='center', va='bottom', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        # 添加端点标记（只标记整个商品组的左右端点）
        ax.scatter([row['position'], right_position], 
                  [y_position, y_position], 
                  color=color, s=30, zorder=5)
    
    # 设置图形属性
    ax.set_xlabel('位置 (毫米)', fontsize=12)
    ax.set_ylabel('', fontsize=12)
    ax.set_title('货架陈列布局图', fontsize=14, fontweight='bold')
    
    # 设置坐标轴范围
    ax.set_xlim(-50, shelf_width + 50)  # 留出一些边距
    ax.set_ylim(0, 1)
    
    # 添加图例
    handles = [
        plt.Line2D([0], [0], color='red', linewidth=3, label='facing ≥ 2'),
        plt.Line2D([0], [0], color='blue', linewidth=2, label='facing = 1'),
        plt.Line2D([0], [0], color='black', linewidth=2, label='货架基线'),
        plt.Line2D([0], [0], color='gray', linestyle='--', label='货架边界'),
        plt.Line2D([0], [0], color='black', linewidth=2, label='商品分界点')
    ]
    ax.legend(handles=handles, loc='upper right')
    
    # 添加网格以便于阅读
    ax.grid(True, alpha=0.3)
    
    # 调整布局
    plt.tight_layout()
    
    return fig

# 更清晰的版本 - 使用矩形表示每个商品
def plot_layer_arrangement_rec(shelf_width, layer_items_df):
    """
    增强版货架排列图 - 使用矩形表示每个商品
    """
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # 设置y轴位置
    y_position = 0.5
    rect_height = 0.3
    
    # 绘制货架基线
    ax.axhline(y=y_position, color='black', linewidth=1, alpha=0.5)
    
    # 绘制货架边界
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.7)
    ax.axvline(x=shelf_width, color='gray', linestyle='--', alpha=0.7)
    
    # 遍历每个商品组
    for idx, row in layer_items_df.iterrows():
        # 计算整个商品组的总宽度
        total_width = row['item_width'] * row['facing']
        
        # 根据facing值选择颜色
        color = 'red' if row['facing'] >= 2 else 'blue'
        alpha = 0.7 if row['facing'] >= 2 else 0.5
        
        # 为每个单独的商品绘制矩形
        for i in range(row['facing']):
            # 计算当前商品的位置
            item_x = row['position'] + i * row['item_width']
            item_y = y_position - rect_height/2
            
            # 绘制矩形表示商品
            rect = patches.Rectangle(
                (item_x, item_y), row['item_width'], rect_height,
                linewidth=1, edgecolor=color, facecolor=color, alpha=alpha
            )
            ax.add_patch(rect)
            
            # 在每个商品内添加编号（只在前几个商品中添加，避免拥挤）
            if i < 3:  # 只在前3个商品中显示编号
                text_x = item_x + row['item_width'] / 2
                text_y = item_y + rect_height / 2
                ax.text(text_x, text_y, row['item_code'], 
                       ha='center', va='center', fontsize=8, color='white', weight='bold')
        
        # 添加商品组信息标注
        text_x = row['position'] + total_width / 2
        text_y = y_position + rect_height/2 + 0.05
        
        label = f"{row['item_code']} (segment_rank:{row['segment_rank']})"
        if row['facing'] > 1:
            label += f" ×{row['facing']}"
            
        ax.text(text_x, text_y, label, 
                ha='center', va='bottom', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
    
    # 设置图形属性
    ax.set_xlabel('位置 (毫米)', fontsize=12)
    ax.set_ylabel('', fontsize=12)
    ax.set_title('货架陈列布局图（增强版）', fontsize=14, fontweight='bold')
    
    # 设置坐标轴范围
    ax.set_xlim(-50, shelf_width + 50)
    ax.set_ylim(0, 1)
    
    # 添加图例
    handles = [
        patches.Patch(color='red', alpha=0.7, label='facing ≥ 2'),
        patches.Patch(color='blue', alpha=0.5, label='facing = 1'),
        plt.Line2D([0], [0], color='gray', linestyle='--', label='货架边界')
    ]
    ax.legend(handles=handles, loc='upper right')
    
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig

def pog_visualize(pog_data, item_attributes_detail, target_module, target_layer, pog_config_org, option = 'rec'):
    layer_mask = (pog_data['module_id'] == target_module) & (pog_data['layer_id'] == target_layer)
    layer_items = pog_data[layer_mask]
    for idx in layer_items.index:
        item_code = layer_items.loc[idx]['item_code']
        item_row_detail = item_attributes_detail[item_attributes_detail['item_idnt'] == int(item_code)]
        segment = item_row_detail.iloc[0]['category_name']
        segment_rank_rule = pog_config_org['segment']['assign_brand_rank']
        segment_rank = int(segment_rank_rule[segment])
        layer_items.loc[idx, 'segment_rank'] = segment_rank
    if option == 'rec':
        fig = plot_layer_arrangement_rec(pog_config_org['global']['module_meter'][target_module - 1], layer_items)
    elif option == 'line':
        fig = plot_layer_arrangement(pog_config_org['global']['module_meter'][target_module - 1], layer_items)
    return fig

# 测试代码
if __name__ == "__main__":
    # 创建示例数据
    data = {
        'item_code': ['A001', 'B002', 'C003', 'D004', 'E005'],
        'position': [0, 200, 500, 800, 1200],
        'item_width': [100, 80, 120, 150, 90],
        'facing': [1, 3, 2, 1, 4],
        'segment_rank': [1, 2, 1, 3, 2]
    }
    
    df = pd.DataFrame(data)
    shelf_width = 1800  # 毫米
    
    # 绘制两种版本的图形
    fig1 = plot_layer_arrangement(shelf_width, df)
    fig2 = plot_layer_arrangement_rec(shelf_width, df)
    
    plt.show()