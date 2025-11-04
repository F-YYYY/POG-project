import pandas as pd
from typing import Dict, Optional, List, Tuple


class RemoveSKU:
    """
    RemoveSKU 类
    ------------------
    从指定 module_id + layer_id 中删除 SKU，
    并禁止删除托盘(tray)或托盘上的商品（只在该层判定）。
    返回 (new_pog, status_dict) 形式（与原流程兼容）。
    """

    def __init__(self):
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.affected_layers_by_removal: List[Tuple[int, int]] = []
        print("✅ RemoveSKU 初始化完成。")

    def remove_sku_items(self, var_dict: Dict):
        pog_data: pd.DataFrame = var_dict['bases_data']['pog_data']
        tray_item_data: Optional[pd.DataFrame] = var_dict['bases_data'].get('tray_item', None)
        params = var_dict['func'].get('del_item_func', {})
        delete_skus = params.get('del_item_list', [])
        target_module_id = params.get('target_module_id', None) or params.get('module_id', None)
        target_layer_id = params.get('target_layer_id', None) or params.get('layer_id', None)

        print(f"\n--- 开始执行 'remove_sku_items' 删除SKU: {delete_skus} ---")
        print(f"🔎 限定检查层：module_id={target_module_id}, layer_id={target_layer_id}")

        # 基本检查
        if pog_data is None or pog_data.empty:
            return pog_data, {'status': 'fail', 'msg': 'POG数据为空'}

        if 'item_code' not in pog_data.columns:
            return pog_data, {'status': 'fail', 'msg': "缺少字段 'item_code'"}

        # 统一类型为字符串，方便比较
        pog_data = pog_data.copy()
        pog_data['item_code'] = pog_data['item_code'].astype(str)

        # 准备 tray-item 映射（只取前两列）
        tray_links: Dict[str, List[str]] = {}
        if tray_item_data is not None and not tray_item_data.empty:
            try:
                tray_pair_df = tray_item_data.iloc[:, [0, 1]].copy()
                tray_pair_df.columns = ['tray_id', 'item_code']
                tray_pair_df['tray_id'] = tray_pair_df['tray_id'].astype(str)
                tray_pair_df['item_code'] = tray_pair_df['item_code'].astype(str)
                for _, r in tray_pair_df.iterrows():
                    tray_links.setdefault(r['item_code'], []).append(r['tray_id'])
                print(f"📦 载入 tray_item 映射，{len(tray_pair_df)} 条记录，映射项数 {len(tray_links)}。")
            except Exception as e:
                print(f"⚠️ 处理 tray_item 文件时出错：{e}")
                tray_links = {}
        else:
            print("ℹ️ 未提供 tray_item 数据或文件为空，跳过 tray-item 映射检查。")

        # 如果用户未给定 target layer，提示报错（按你的设计需要指定）
        if target_module_id is None or target_layer_id is None:
            return pog_data, {'status': 'fail', 'msg': '请提供 target_module_id 和 target_layer_id（例如 6 / 2）'}

        # 取出目标层数据（只在该层内查找 SKU）
        layer_df = pog_data[
            (pog_data['module_id'] == target_module_id) &
            (pog_data['layer_id'] == target_layer_id)
        ].copy()

        if layer_df.empty:
            return pog_data, {'status': 'fail', 'msg': f'未找到指定层：module_id={target_module_id}, layer_id={target_layer_id}（该层无记录）'}

        # 层内有哪些 tray（tray 的 item_code 在 pog 数据中一般表示 tray_id）
        tray_ids_in_layer: List[str] = []
        if 'item_type' in layer_df.columns:
            tray_ids_in_layer = layer_df.loc[layer_df['item_type'] == 'tray', 'item_code'].astype(str).tolist()

        # 检查每个待删除 SKU（只在本层判断）
        for code in delete_skus:
            code_str = str(code)
            # 1) 是否存在于本层（item 或 tray）
            exists_in_layer = not layer_df[layer_df['item_code'] == code_str].empty
            if not exists_in_layer:
                return pog_data, {'status': 'fail', 'msg': f'未找到商品：SKU {code_str} 不存在于指定层 module_id={target_module_id}, layer_id={target_layer_id}。'}

            # 2) 是否为本层的 tray（即直接是 tray 本身）
            if 'item_type' in layer_df.columns:
                row_is_tray = not layer_df[(layer_df['item_code'] == code_str) & (layer_df['item_type'] == 'tray')].empty
                if row_is_tray:
                    return pog_data, {'status': 'fail', 'msg': f'删除失败：SKU {code_str} 是本层的托盘(tray)，禁止删除。'}

            # 3) 是否属于本层的 tray（即 tray_item.csv 将该 SKU 关联到了本层的某个 tray_id）
            if code_str in tray_links and tray_ids_in_layer:
                linked_trays = tray_links[code_str]
                intersect = set(linked_trays).intersection(set(tray_ids_in_layer))
                if intersect:
                    t_id = list(intersect)[0]
                    return pog_data, {
                        'status': 'fail',
                        'msg': f'删除失败：SKU {code_str} 位于指定层的托盘 {t_id} 上（module_id={target_module_id}, layer_id={target_layer_id}），禁止删除。'
                    }

        # 通过所有检查，执行删除 —— 只删除在目标层中的这些 SKU，其他层相同 SKU 不受影响
        cond_not_deleted = ~(
            (pog_data['item_code'].isin([str(x) for x in delete_skus])) &
            (pog_data['module_id'] == target_module_id) &
            (pog_data['layer_id'] == target_layer_id)
        )
        new_pog = pog_data.loc[cond_not_deleted].copy()
        removed_num = len(pog_data) - len(new_pog)

        # 记录受影响层（只有目标层）
        self.affected_layers_by_removal = [(target_module_id, target_layer_id)]

        print(f"🗑️ 已从指定层删除 {removed_num} 条 SKU（仅限指定层）。")
        return new_pog, {'status': 'success', 'msg': f'成功删除 {removed_num} 个SKU', 'deleted_skus': delete_skus}


class FillLayerSKU(RemoveSKU):
    """
    FillLayerSKU 类
    ------------------
    删除SKU后：
    1. 计算剩余空间
    2. 使用 0-1 动态规划（Knapsack）在剩余宽度下选一组 SKU 的额外 facing（每个 SKU 最多 +1）以最大化 revenue
    3. 若无法增加任何 facing，则仅等距重排（含两端空隙）
    """

    def __init__(self):
        super().__init__()
        self.affected_layer_space: Optional[pd.DataFrame] = None
        self.sorted_items_by_position: Dict[Tuple[int, int], pd.DataFrame] = {}
        self.sales_df: Optional[pd.DataFrame] = None
        # 背包基准宽度 — 按你之前约定用 995mm 作为上限基准（可修改）
        self.dp_capacity_baseline = 995
        print("✅ FillLayerSKU 初始化完成。")

    def analyze_layer_space(self, pog_data: pd.DataFrame, total_layer_width: int = None) -> pd.DataFrame:
        # 如果未传 total_layer_width，则使用 baseline（以便保持一致）
        if total_layer_width is None:
            total_layer_width = self.dp_capacity_baseline
        if pog_data.empty:
            return pd.DataFrame(columns=['module_id', 'layer_id', 'item_count', 'used_width', 'remaining_width'])
        layer_summary = pog_data.groupby(['module_id', 'layer_id']).agg(
            used_width=('item_width', 'sum'),
            item_count=('item_code', 'count')
        ).reset_index()
        layer_summary['total_width'] = total_layer_width
        layer_summary['remaining_width'] = layer_summary['total_width'] - layer_summary['used_width']
        return layer_summary

    def calculate_space_for_affected_layers(self, pog_data: pd.DataFrame, total_layer_width: int = None):
        print("\n--- 计算受影响层剩余空间 ---")
        if total_layer_width is None:
            total_layer_width = self.dp_capacity_baseline
        if not self.affected_layers_by_removal:
            print("ℹ️ 无受影响层。")
            return
        all_layers = self.analyze_layer_space(pog_data, total_layer_width)
        affected = all_layers.set_index(['module_id', 'layer_id']).reindex(self.affected_layers_by_removal)
        self.affected_layer_space = affected.reset_index()
        print("✅ 受影响层空间计算完成。")

    def sort_items_by_position(self, pog_data: pd.DataFrame):
        print("\n--- 排序受影响层内商品 ---")
        self.sorted_items_by_position.clear()
        for mod_id, lay_id in self.affected_layers_by_removal:
            df = pog_data[(pog_data['module_id'] == mod_id) & (pog_data['layer_id'] == lay_id)].copy()
            if df.empty:
                continue
            sorted_df = df.sort_values(by='position')
            self.sorted_items_by_position[(mod_id, lay_id)] = sorted_df
        print("✅ 排序完成。")

    @staticmethod
    def _knapsack_01(weights: List[int], values: List[float], capacity: int):
        """
        0-1 knapsack dynamic programming (returns indices selected)
        weights: list of positive ints
        values: list of floats (values)
        capacity: int capacity
        返回: set(selected indices)
        """
        n = len(weights)
        if n == 0 or capacity <= 0:
            return set()

        # dp[w] = max value achievable with capacity w
        dp = [0.0] * (capacity + 1)
        # keep choice info: for reconstruction, keep a 2D predecessor or use item-based backtracking table
        # 为节省内存，用二维表记录是否选择 item i at capacity w
        choose = [[False] * (capacity + 1) for _ in range(n)]

        for i in range(n):
            wt = weights[i]
            val = values[i]
            # traverse capacity descending for 0-1 knapsack
            for w in range(capacity, wt - 1, -1):
                if dp[w - wt] + val > dp[w]:
                    dp[w] = dp[w - wt] + val
                    choose[i][w] = True

        # reconstruct chosen indices
        w = capacity
        chosen = set()
        for i in range(n - 1, -1, -1):
            if w >= 0 and choose[i][w]:
                chosen.add(i)
                w -= weights[i]

        return chosen

    def fill_and_reposition_layers(self, pog_data: pd.DataFrame, total_layer_width: int = None):
        """
        使用 0-1 DP 选出要增加的 facing（每个 SKU 最多 +1）。
        重排时采用“两端留空”的等距分布（与原逻辑保持一致）。
        """
        if total_layer_width is None:
            total_layer_width = self.dp_capacity_baseline

        print("\n--- 开始执行 DP-based 填充与重新定位（0-1 Knapsack） ---")
        updated_layers = []

        for layer_key, layer_df in self.sorted_items_by_position.items():
            mod_id, lay_id = layer_key
            print(f"\n处理层：module {mod_id} - layer {lay_id}")

            # 获取该层剩余宽度（基于 analyze_layer_space 的 baseline）
            layer_space = self.analyze_layer_space(pog_data, total_layer_width)
            remain_series = layer_space[
                (layer_space['module_id'] == mod_id) &
                (layer_space['layer_id'] == lay_id)
            ]['remaining_width']
            if remain_series.empty:
                print(f"⚠️ 无法读取层 {mod_id}-{lay_id} 的剩余宽度，跳过。")
                continue
            remaining_width = int(max(0, int(remain_series.iloc[0])))  # 转为整数毫米
            print(f"剩余宽度（capacity）: {remaining_width} mm")

            # 仅考虑非 tray items 作为 candidate（且必须在该层存在）
            candidates_df = layer_df.copy()
            if 'item_type' in candidates_df.columns:
                candidates_df = candidates_df[candidates_df['item_type'] != 'tray'].copy()
            if candidates_df.empty:
                print("无候选商品（非tray），跳过该层。")
                # 仍需重排以保证间距一致 -> 但若无变化可直接跳过
                continue

            # 计算 revenue = sales * qty（sales_df 已在 run_delete_fill_pipeline 里预处理）
            # 将 revenue 合并进候选
            cand = candidates_df.copy()
            if self.sales_df is not None:
                # sales_df 已包含 item_code (str) 与 revenue 字段
                cand = cand.merge(self.sales_df[['item_code', 'revenue']], on='item_code', how='left')
                cand['revenue'] = cand['revenue'].fillna(0.0)
            else:
                cand['revenue'] = 0.0

            # weights / values for DP
            weights: List[int] = cand['item_width'].astype(int).tolist()
            values: List[float] = cand['revenue'].astype(float).tolist()

            # filter out items whose width > remaining_width (they can't be added)
            feasible_idx = [i for i, w in enumerate(weights) if w <= remaining_width and w > 0]
            if not feasible_idx:
                print("没有宽度可放下的候选商品，执行等距重排。")
                # 按照原逻辑做等距重排（无新增 facing）
                new_items = []
                for _, row in layer_df.iterrows():
                    new_items.append(row.to_dict())
                total_width = sum(i['item_width'] for i in new_items)
                spacing = (total_layer_width - total_width) / (len(new_items) + 1) if len(new_items) > 0 else 0
                pos = spacing
                for item in new_items:
                    item['position'] = pos
                    pos += item['item_width'] + spacing
                updated_layers.append(pd.DataFrame(new_items))
                continue

            # prepare arrays limited to candidates
            cand_weights = [weights[i] for i in feasible_idx]
            cand_values = [values[i] for i in feasible_idx]

            # run knapsack (capacity = remaining_width)
            chosen_indices_local = self._knapsack_01(cand_weights, cand_values, remaining_width)

            # map back to original candidate indices
            chosen_global_idx = [feasible_idx[i] for i in chosen_indices_local]

            picked_codes = set()
            for idx in chosen_global_idx:
                picked_codes.add(str(cand.iloc[idx]['item_code']))

            if picked_codes:
                total_gain = sum(float(cand.iloc[idx]['revenue']) for idx in chosen_global_idx)
                print(f"DP 选择的 SKU 集合: {picked_codes}，预计额外 revenue: {total_gain:.3f}")
            else:
                print("DP 未选择任何额外 facing（或收益为0），进行等距重排。")

            # 构建新层数据（原件 + 复制品）
            new_items = []
            # we iterate original layer_df order (sorted by position)
            for _, row in layer_df.iterrows():
                new_items.append(row.to_dict())
                if str(row['item_code']) in picked_codes:
                    copy = row.to_dict()
                    copy['position'] = -1
                    # 标记复制的行可以用某标志位（例如 facing=2 或新增字段），但这里保留原结构，仅新增一行
                    new_items.append(copy)

            # 计算等距位置（两端空）
            total_width = sum(i['item_width'] for i in new_items)
            num_items = len(new_items)
            spacing = (total_layer_width - total_width) / (num_items + 1) if num_items > 0 else 0
            pos = spacing
            for item in new_items:
                item['position'] = pos
                pos += item['item_width'] + spacing

            updated_layers.append(pd.DataFrame(new_items))

        # 合并更新层与未受影响层
        if not updated_layers:
            return pog_data, {'status': 'success', 'msg': '无可更新层'}

        new_layers = pd.concat(updated_layers, ignore_index=True)
        unaffected = pog_data.set_index(['module_id', 'layer_id']).drop(
            index=pd.MultiIndex.from_tuples(self.affected_layers_by_removal, names=['module_id', 'layer_id']),
            errors='ignore'
        ).reset_index()
        new_pog = pd.concat([unaffected, new_layers], ignore_index=True)

        print("✅ DP-based 填充与重新定位完成。")
        return new_pog, {'status': 'success', 'msg': '填充与重新定位成功'}

    def run_delete_fill_pipeline(self, var_dict: Dict) -> Tuple[pd.DataFrame, Dict]:
        # 统一 item_code 为 str
        pog_data = var_dict['bases_data']['pog_data']
        pog_data = pog_data.copy()
        pog_data['item_code'] = pog_data['item_code'].astype(str)
        var_dict['bases_data']['pog_data'] = pog_data

        # load sales and compute revenue = sales * qty (if provided)
        sales_df = var_dict['bases_data'].get('sales_item_sum', None)
        if sales_df is not None and not sales_df.empty:
            sales_df = sales_df.copy()
            # ensure columns
            if 'item_code' in sales_df.columns and 'sales' in sales_df.columns and 'qty' in sales_df.columns:
                sales_df['item_code'] = sales_df['item_code'].astype(str)
                sales_df['revenue'] = sales_df['sales'].astype(float) * sales_df['qty'].astype(float)
                self.sales_df = sales_df[['item_code', 'revenue']].copy()
                print("✅ 已载入 sales_item_sum，并计算 revenue = sales * qty。")
            else:
                print("⚠️ sales_item_sum 文件缺少必要列 (item_code, sales, qty)。将默认 revenue=0。")
                self.sales_df = None
        else:
            print("ℹ️ 未提供 sales_item_sum，double 选择默认 revenue=0。")
            self.sales_df = None

        # step1: 删除（限定层）
        new_pog, status = self.remove_sku_items(var_dict)
        if status.get('status') == 'fail':
            return new_pog, status

        # step2: 计算受影响层空间并排序
        self.calculate_space_for_affected_layers(new_pog)
        self.sort_items_by_position(new_pog)

        # step3: 使用 DP 进行填充与重排
        final_pog, status2 = self.fill_and_reposition_layers(new_pog)
        return final_pog, status2


# ===========================
# ✅ 示例调用
# ===========================
if __name__ == "__main__":
    pog_file = r"C:\Users\fy\Desktop\POG\新的\开发所需测试数据\开发所需测试数据\pog_result.csv"
    tray_item_file = r"C:\Users\fy\Desktop\POG\新的\开发所需测试数据\开发所需测试数据\pog_test_haircare_tray_item.csv"
    sales_file = r"C:\Users\fy\Desktop\POG\新的\开发所需测试数据\开发所需测试数据\sales_item_sum.csv"

    var_dict = {
        'bases_data': {
            'pog_data': pd.read_csv(pog_file),
            'tray_item': pd.read_csv(tray_item_file),
            'sales_item_sum': pd.read_csv(sales_file)
        },
        'func': {
            'del_item_func': {
                'del_item_list': ['101473131'],
                'target_module_id': 6,
                'target_layer_id': 2
            }
        }
    }

    filler = FillLayerSKU()
    new_pog, status = filler.run_delete_fill_pipeline(var_dict)

    print(status)
    if status['status'] == 'success':
        output_file = r"C:\Users\fy\Desktop\POG\新的\开发所需测试数据\开发所需测试数据\pog_result_final_output.csv"
        new_pog.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 最终结果已导出至: {output_file}")
    else:
        print("❌ 操作失败：", status.get('msg', '未知错误'))
