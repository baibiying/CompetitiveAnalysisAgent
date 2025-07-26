from openai import OpenAI
import json
 
client = OpenAI(
    api_key = "sk-JGwNBDB0CQ9biJdN13MR2ZVfgnoGjYA0THoUIxw7z7WMDHFh",
    base_url = "https://api.moonshot.cn/v1",
)

def desicion(budget, special_remark, available_fruits):
    completion = client.chat.completions.create(
        model = "kimi-k2-0711-preview",
        messages = [
            {"role": "system", "content": "你是水果市场研究专家，需按以下逻辑和格式完成任务：\n"
            "1. 信息接收：精准提取用户提供的「预算范围」「特别备注（如口味偏好、食用场景、禁忌等）」及「可选择的水果品种列表」，所有已知信息均为判断核心依据；\n"
            "2. 排序依据：按以下维度（权重从高到低）对可选择品种排序 ——\n - 适配性（40%）：是否完全匹配特别备注（如 “榨汁用” 优先出汁率高品种，“送礼” 优先包装 / 品牌优质品种）；\n"
            " - 性价比（30%）：该品种是否存在价格超出目前该品种的市场价（如某品种，目前市场价为10元/斤，售价为15元/斤，则该品种不合适）；以及考虑在预算内的价格合理性（如优先考虑单价在预算内且品质达标的品种）；\n "
            "- 综合优势（30%）：新鲜度、口感、品牌认可度等市场公认优势；\n"
            "3. 输出要求：\n "
            "最终推荐以JSON格式输出，仅保留推荐排名第一的水果：键为具体水果名，值为推荐理由（需明确关联预算、特别备注及排序维度"
            ""},
            {"role": "user", "content": 
            "已知：\n-"
            f"- 预算：{budget} \n"
            f"- 特别备注：{special_remark} \n"
            f"- 可选择的品种以及对应参数：{available_fruits} \n "
            "请按要求推荐并说明理由。"}
            ],
            temperature = 0.6,
        )
    
    output = completion.choices[0].message.content
    print(output)
    return output



