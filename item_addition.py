import pandas as pd
import numpy as np

def add_item_func(var_dict):
    """
    新增一个品，旧品不动 - 场景函数
    
    参数:
    var_dict: 包含基础数据和函数参数的字典
    
    返回:
    dict: 包含新pog_data和状态信息的字典
    """
    # try:
        # 从var_dict中获取基础数据
    bases_data = var_dict['bases_data']
    pog_data = bases_data['pog_data'].copy()
    tray_item = bases_data['tray_item']
    item_attributes = bases_data['item_attributes']
    item_attributes_detail = bases_data['item_attributes_detail']
    sales_data = bases_data['sales_data']
    brand_2_brand_label = bases_data['brand_2_brand_label']
    
    # 从var_dict中获取即将添加的商品编号
    add_item_code = var_dict['add_item']
    
    # Step1：检查是否为托盘商品
    add_item_info = get_item_info(add_item_code, item_attributes, item_attributes_detail, brand_2_brand_label)
    if add_item_info == None:
        return {
            'pog_data': pog_data,
            'status': 'fail',
            'error_msg': f'未找到商品标号 {add_item_code}相应的商品信息 '
        }
    if is_tray_item(add_item_code):
        return {
            'pog_data': pog_data,
            'status': 'fail',
            'error_msg': f'新增的商品 {add_item_code} 是托盘商品，不能在商品区域陈列'
        }
    
    # Step2：定位商品位置
    position_result = locate_item_position(add_item_code, pog_data, item_attributes, item_attributes_detail, brand_2_brand_label)
    if not position_result['success']:
        return {
            'pog_data': pog_data,
            'status': 'fail',
            'error_msg': position_result['error_msg']
        }
    
    target_module = position_result['module']
    target_layer = position_result['layer']
    matching_level = position_result['matching_level']
    add_item_width = add_item_info['width']
    
    # Step3：尝试在目标层插入商品
    pog_info_dict = {
        'item_attributes' : item_attributes, 
        'item_attributes_detail' : item_attributes_detail, 
        'brand_2_brand_label' : brand_2_brand_label,
        'sales_data' : sales_data
    }   # 在层内再次进行定位时需要用到的商品细节信息
    insert_result = insert_item_to_target_layer(
        pog_data, add_item_code, add_item_width, target_module, target_layer, matching_level, pog_info_dict
    )
    
    if insert_result['success']:
        return {
            'pog_data': insert_result['new_pog_data'],
            'status': 'success',
            'error_msg': '',
            'target_module': target_module,
            'target_layer': target_layer
        }
    else:
        return {
            'pog_data': pog_data,
            'status': 'fail',
            'error_msg': insert_result['error_msg']
        }
        
    # except Exception as e:
    #     return {
    #         'pog_data': pog_data,
    #         'status': 'fail',
    #         'error_msg': f'函数执行出错: {str(e)}'
    #     }

def is_tray_item(item_code):
    """检查商品是否为托盘商品且不能在商品区域陈列"""
    if int(item_code) < 1000000:
        return True
    else:
        return False
    # TODO：这里先用最简单的实现方法，具体逻辑有待确认和推敲

def locate_item_position(item_code, pog_data, item_attributes, item_attributes_detail, brand_2_brand_label):
    """
    定位商品应该放在哪个模块和层
    按照品牌层级结构从细到粗查找
    """
    # 获取商品属性
    item_info = get_item_info(item_code, item_attributes, item_attributes_detail, brand_2_brand_label)
    if item_info is None:
        return {
            'success': False,
            'error_msg': f'未找到商品 {item_code} 的属性信息'
        }

    # 获取商品的品牌层级信息
    series = item_info['series']
    brand = item_info['brand']
    brand_label = item_info['brand_label']
        
    # 遍历现有pog_data中的所有商品，寻找匹配商品的位置
    matching_result = None
    current_level = 0  # 0:无匹配, 1:品牌集合, 2:品牌, 3:系列
    # 第一次遍历，确定匹配层级
    for idx in range(0, len(pog_data)):
        matching_item_code = pog_data.iloc[idx]['item_code']
        # 若为托盘商品，暂时直接跳过
        if is_tray_item(matching_item_code):
            continue
        # 若当前pog布局中正好有正在添加的item，直接返回
        if matching_item_code == item_code:
            return {
                'module' : pog_data.iloc[idx]['module_id'],
                'layer' : pog_data.iloc[idx]['layer_id'],
                'matching_item_code' : matching_item_code,
                'matching_level' : 'same_item',
                'success': True
            }

        matching_item_info = get_item_info(matching_item_code, item_attributes, item_attributes_detail, brand_2_brand_label)
        matching_series = matching_item_info['series']
        matching_brand = matching_item_info['brand']
        matching_brand_label = matching_item_info['brand_label']
        if matching_brand_label == brand_label:
            if matching_brand == brand:
                if matching_series == series:   # 品牌集合、品牌、系列皆匹配
                    matching_result = {
                    'module' : pog_data.iloc[idx]['module_id'],
                    'layer' : pog_data.iloc[idx]['layer_id'],
                    'matching_item_code' : matching_item_code,
                    'matching_index' : idx,
                    'matching_level' : 'series',
                    'name_for_searching_layer' : matching_series    # 用于第二次遍历匹配的系列名
                    }
                    current_level = 3
                elif current_level < 2:   # 仅品牌集合、品牌匹配，且当前的匹配等级较小
                    matching_result = {
                    'module' : pog_data.iloc[idx]['module_id'],
                    'layer' : pog_data.iloc[idx]['layer_id'],
                    'matching_item_code' : matching_item_code,
                    'matching_index' : idx,
                    'matching_level' : 'brand',
                    'name_for_searching_layer' : matching_brand     # 用于第二次遍历匹配的系列名
                    }
                    current_level = 2
            elif current_level < 1:   # 仅品牌集合匹配，且当前无匹配
                matching_result = {
                    'module' : pog_data.iloc[idx]['module_id'],
                    'layer' : pog_data.iloc[idx]['layer_id'],
                    'matching_item_code' : matching_item_code,
                    'matching_index' : idx,
                    'matching_level' : 'brand_label',
                    'name_for_searching_layer' : matching_brand_label   # 用于第二次遍历匹配的品牌集合名    
                    }
                current_level = 1
    # 如果所有层级都找不到匹配
    if current_level == 0:
        return {
        'success': False,
        'error_msg': f'无法为商品 {item_code} 匹配到相同的商品层级'
    }

    # 第二次遍历现有pog_data，根据匹配的层级，查找匹配层级的所有layer
    optional_layer = [] # 用于存储所有同level的layer
    matching_level = matching_result['matching_level']
    matching_index = matching_result['matching_index']
    for idx in range(matching_index , len(pog_data)):
        matching_item_code = pog_data.iloc[idx]['item_code']
        if is_tray_item(matching_item_code):
            continue
        matching_item_info = get_item_info(matching_item_code, item_attributes, item_attributes_detail, brand_2_brand_label)
        matching_level_name = matching_item_info.get(matching_level)
        if matching_level_name == matching_result['name_for_searching_layer']:
            # 记录位置，并计算剩余空间
            module_id = pog_data.iloc[idx]['module_id']
            layer_id = pog_data.iloc[idx]['layer_id']
            remaining_space = calculate_layer_space(module_id, layer_id, pog_data)
            layer_info = {'module_id' : module_id, 
                            'layer_id' : layer_id, 
                            'remaining_space' : remaining_space}
            optional_layer.append(layer_info)   # TODO:这里可能会重复添加已有layer，有空再优化

    # 再从符合条件的layer里面挑选出可供插入的最大空间layer
    max_space_layer = max(optional_layer,  key=lambda x: x['remaining_space'])
    return {
        'module': max_space_layer['module_id'],
        'layer': max_space_layer['layer_id'],
        'matching_item_code' : matching_result['matching_item_code'],
        'matching_level' : matching_result['matching_level'],
        'success': True
    }


def get_item_info(item_code, item_attributes, item_attributes_detail, brand_2_brand_label):
    """获取商品的完整属性信息"""
    # 从商品属性表获取基本信息
    item_row = item_attributes[item_attributes['ITEM_NBR'] == int(item_code)]
    item_row_detail = item_attributes_detail[item_attributes_detail['item_idnt'] == int(item_code)]
    brand_name = item_row_detail.iloc[0]['brandname_cn']
    brand_row = brand_2_brand_label[brand_2_brand_label['brand'] == brand_name]
    if item_row.empty or item_row_detail.empty or brand_row.empty:     # 暂时只考虑添加在三个表中都有信息的商品
        return None
    
    item_width = item_row_detail.iloc[0]['item_breadth'] * 10 # ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V.csv表使用的单位为cm，需要换算
    item_info = {
        'item_code': item_code,
        'series': item_row.iloc[0]['SERIES'],
        'item_name': item_row.iloc[0]['ITEM_NAME'],
        'width': item_width,
        'brand' : brand_name,
        'brand_label' : brand_row.iloc[0]['brand_label']
    }

    return item_info

def calculate_layer_space(module_id, layer_id, pog_data):
    """计算匹配商品所在各层的剩余空间"""

    # 获取该层的所有商品
    layer_items = pog_data[
            (pog_data['module_id'] == module_id) & 
            (pog_data['layer_id'] == layer_id)
        ]
        
    if layer_items.empty:
            return 0
            
    module_width = layer_items['module_width'].iloc[0]
    layer_items['total_item_width'] = layer_items['item_width'] * layer_items['facing']
    used_space = layer_items['total_item_width'].sum()
    remaining_space = module_width - used_space
    
    return remaining_space

def insert_item_to_target_layer(pog_data, item_code, item_width, target_module, target_layer, matching_level, pog_info_dict):
    """在目标层插入商品"""
    new_pog_data = pog_data.copy()
    
    # 获取目标层的所有商品
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    layer_items = new_pog_data[layer_mask]
    
    if layer_items.empty:
        # 如果该层没有商品，直接添加
        result = add_item_to_empty_layer(new_pog_data, item_code, item_width, target_module, target_layer)
        if result['success']:
            return {'success': True, 'new_pog_data': result['new_pog_data']}
        else:
            return {'success': False, 'error_msg': result['error_msg']}
    
    # 计算当前剩余空间
    # module_width = layer_items['module_width'].iloc[0]
    # current_used_space = layer_items['item_width'].sum()
    current_remaining_space = calculate_layer_space(target_module, target_layer, pog_data)
    
    if current_remaining_space >= item_width:
        # 空间足够，直接插入并重排
        result = insert_and_rearrange(new_pog_data, item_code, item_width, target_module, target_layer, matching_level, pog_info_dict)
        if result['success']:
            return {'success': True, 'new_pog_data': result['new_pog_data']}
        else:
            return {'success': False, 'error_msg': result['error_msg']}
    else:
        # 空间不足，尝试调整策略
        return adjust_space_for_insertion(new_pog_data, item_code, item_width, target_module, target_layer, pog_info_dict['sales_data'])

def add_item_to_empty_layer(pog_data, item_code, item_width, target_module, target_layer):
    """向空层添加商品"""
    new_pog_data = pog_data.copy()
    
    # 获取模块宽度
    module_info = new_pog_data[new_pog_data['module_id'] == target_module].iloc[0]
    module_width = module_info['module_width']
    
    # 创建新商品行
    new_row = create_new_item_row(new_pog_data, item_code, item_width, target_module, target_layer, 0)
    new_pog_data = pd.concat([new_pog_data, pd.DataFrame([new_row])], ignore_index=True)
    
    return {'success': True, 'new_pog_data': new_pog_data}

def insert_and_rearrange(pog_data, item_code, item_width, target_module, target_layer, matching_level, pog_info_dict):
    """插入商品并重排位置"""
    new_pog_data = pog_data.copy()

    if matching_level == 'same_item':
        new_pog_data.loc[new_pog_data['item_code'] == item_code, 'facing'] += 1 # 直接令facing+1
    else:
        # 在末尾添加商品
        layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
        layer_items = new_pog_data[layer_mask]
        
        if layer_items.empty:
            return add_item_to_empty_layer(new_pog_data, item_code, item_width, target_module, target_layer)
        
        # 创建新商品行（临时位置-1）
        new_row = create_new_item_row(new_pog_data, item_code, item_width, target_module, target_layer, -1)
        new_pog_data = pd.concat([new_pog_data, pd.DataFrame([new_row])], ignore_index=True)
        
        # 确定新商品在层内应摆的位置
        item_attributes = pog_info_dict['item_attributes']
        item_attributes_detail = pog_info_dict['item_attributes_detail']
        brand_2_brand_label = pog_info_dict['brand_2_brand_label']

        sorted_layer_items = layer_items.sort_values(by = 'position', ascending = True)
        position_result = locate_item_position(item_code, sorted_layer_items, item_attributes, item_attributes_detail, brand_2_brand_label)
        matching_item_code = position_result['matching_item_code']
        new_pog_data.loc[len(new_pog_data)-1, 'position'] = (sorted_layer_items[sorted_layer_items['item_code'] == matching_item_code].iloc[0]['position'] - 0.5)      # 直接将新加入的商品插在前面（这里修改的列索引不知道为什么必须是len(new_pog_data)-1）
            
    
    # 调整该层所有商品的间距
    new_pog_data = rearrange_layer_item_gap(new_pog_data, target_module, target_layer)
    
    return {'success': True, 'new_pog_data': new_pog_data}

def create_new_item_row(pog_data, item_code, item_width, target_module, target_layer, position):
    """创建新商品的数据行"""
    # 获取参考行用于填充其他字段
    ref_row = pog_data.iloc[0].copy()   
    
    # 构建新行
    new_row = {
        'req_id': pog_data['req_id'].max() + 1,
        'picture_id': ref_row['picture_id'],    # TODO：这里需要根据后续图片数据来调整
        'item_code': item_code,
        'module_id': target_module,
        'module': chr(64 + target_module),  # 1->A, 2->B, ...
        'layer_id': target_layer,
        'position': position,
        'item_width': item_width,
        'facing': 1,   # 添加货架上不存在的商品时，facing默认为1
        'item_type': 'item',
        'vert_facing': 1,
        'module_width': ref_row['module_width']
    }
    
    return new_row

def rearrange_layer_item_gap(pog_data, target_module, target_layer):
    """调整指定层的平均间隔"""
    new_pog_data = pog_data.copy()
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    layer_items = new_pog_data[layer_mask]
    sorted_layer_items = layer_items.sort_values(by = 'position', ascending = True)
    sorted_layer_indices = sorted_layer_items.index 
    
    
    if len(sorted_layer_indices) == 0:
        return new_pog_data
    
    # module_width = new_pog_data.loc[layer_indices[0], 'module_width']
    # total_item_width = new_pog_data.loc[layer_indices, 'item_width'].sum()
    
    # 计算平均间隔
    total_gap = calculate_layer_space(target_module, target_layer, pog_data)
    gap_cnt = len(sorted_layer_indices) - 1    # 空隙数量
    avg_gap = total_gap / gap_cnt if gap_cnt > 0 else 0
    ceil_cnt = int(total_gap % gap_cnt)  # 向上取整的空隙数量
    
    # 重新分配位置
    current_position = 0
    for idx in sorted_layer_indices[range(0, ceil_cnt)]:
        new_pog_data.loc[idx, 'position'] = current_position
        current_position += new_pog_data.loc[idx, 'item_width'] * new_pog_data.loc[idx, 'facing'] + np.ceil(avg_gap)
    for idx in sorted_layer_indices[range(ceil_cnt, len(sorted_layer_indices))]:
        new_pog_data.loc[idx, 'position'] = current_position
        current_position += new_pog_data.loc[idx, 'item_width'] * new_pog_data.loc[idx, 'facing'] + np.floor(avg_gap)
    
    return new_pog_data

def adjust_space_for_insertion(pog_data, item_code, item_width, target_module, target_layer, sales_data):
    """调整空间策略：减少facing或删除商品"""
    new_pog_data = pog_data.copy()
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    
    # 策略1: 尝试减少double facing商品的facing
    double_facing_items = new_pog_data[layer_mask & (new_pog_data['facing'] > 1)]
    
    if not double_facing_items.empty:
        # 获取销售数据并排序（从低到高）
        sorted_items = get_sorted_items_by_sales(double_facing_items, sales_data, ascending=True)
        
        for idx in sorted_items.index:
            # 减少一个facing
            original_facing = new_pog_data.loc[idx, 'facing']
            new_pog_data.loc[idx, 'facing'] = original_facing - 1
            
            # 检查空间是否足够
            layer_items_after_adjust = new_pog_data[layer_mask]
            module_width = layer_items_after_adjust['module_width'].iloc[0]
            used_space_after = layer_items_after_adjust['item_width'].sum()
            remaining_space_after = module_width - used_space_after
            
            if remaining_space_after >= item_width:
                # 空间足够，插入商品
                result = insert_and_rearrange(new_pog_data, item_code, item_width, target_module, target_layer) # TODO：函数有变，待改
                if result['success']:
                    return {'success': True, 'new_pog_data': result['new_pog_data']}
            
            # 如果还是不够，恢复原状继续尝试下一个
            new_pog_data.loc[idx, 'facing'] = original_facing
    
    # 策略2: 删除销售最低的商品
    layer_items = new_pog_data[layer_mask]
    if len(layer_items) > 1:
        # 获取销售数据并排序（从低到高）
        sorted_items = get_sorted_items_by_sales(layer_items, sales_data, ascending=True)
        
        for idx in sorted_items.index:
            # 删除一个商品
            temp_pog_data = new_pog_data.drop(index=idx)
            
            # 检查空间是否足够
            temp_layer_items = temp_pog_data[
                (temp_pog_data['module_id'] == target_module) & 
                (temp_pog_data['layer_id'] == target_layer)
            ]
            module_width = temp_layer_items['module_width'].iloc[0]
            used_space_after = temp_layer_items['item_width'].sum()
            remaining_space_after = module_width - used_space_after
            
            if remaining_space_after >= item_width:
                # 空间足够，插入商品
                result = insert_and_rearrange(temp_pog_data, item_code, item_width, target_module, target_layer)    # TODO：函数有变，待改
                if result['success']:
                    return {'success': True, 'new_pog_data': result['new_pog_data']}
    
    # 所有策略都失败
    return {
        'success': False, 
        'error_msg': f'空间不足，无法添加商品 {item_code}，即使调整facing和删除商品后仍然无法容纳'
    }

def get_sorted_items_by_sales(items_df, sales_data, ascending=True):
    """根据销售数据对商品进行排序"""
    # 合并销售数据
    merged_df = items_df.merge(
        sales_data, 
        left_on='item_code', 
        right_on='item_code', 
        how='left'
    )
    
    # 填充缺失的销售数据
    merged_df['sales'] = merged_df['sales'].fillna(0)
    
    # 按销售排序
    return merged_df.sort_values('sales', ascending=ascending)

# 使用示例
if __name__ == "__main__":
    # 数据加载
    pog_result = pd.read_csv('pog_result.csv')
    pog_test_haircare_tray = pd.read_csv('pog_test_haircare_tray.csv')
    pog_test_haircare_test = pd.read_csv('pog_test_haircare_test.csv')
    ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V = pd.read_csv('ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V.csv')
    brand_2_brand_label = pd.read_csv('brand_2_brand_label.csv')
    sales_item_sum = pd.read_csv('sales_item_sum.csv')
    
    # 构建var_dict
    var_dict = {
        'bases_data': {
            'pog_data': pog_result,
            'tray_item': pog_test_haircare_tray,
            'item_attributes': pog_test_haircare_test,
            'item_attributes_detail': ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V,
            'brand_2_brand_label': brand_2_brand_label,
            'sales_data': sales_item_sum
        },
        'add_item': 100006545  # 匹配等级：series
        # 'add_item': 101437322   # 匹配等级：brand_label
        # 'add_item': 101426154   # 匹配等级：brand
    }
    
    # 执行函数
    result = add_item_func(var_dict)
    
    print(f"执行状态: {result['status']}")
    if result['status'] == 'success':
        result['pog_data'].to_csv('add_pog_result.csv', index=False)
        print("商品添加成功！")
        print(f"新pog_data形状: {result['pog_data'].shape}")
    else:
        print(f"错误信息: {result['error_msg']}")