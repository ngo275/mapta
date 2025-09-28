#!/usr/bin/env python3

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict, Counter
import re

plt.rcParams.update({
    'font.size': 16,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'serif'],
    'axes.titlesize': 20,
    'axes.labelsize': 18,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 16,
    'figure.titlesize': 22,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 1.2,
    'xtick.major.size': 6,
    'ytick.major.size': 6,
    'xtick.minor.size': 3,
    'ytick.minor.size': 3,
    'legend.frameon': True,
    'legend.framealpha': 0.9,
    'legend.fancybox': True,
    'legend.shadow': True
})

# Unified color scheme for all plots
COLORS = {
    'solved': '#27AE60',      # Original green for solved
    'failed': '#E74C3C',      # Red for failed  
    'primary': '#3498DB',     # Blue for primary elements
    'secondary': '#F39C12',   # Orange for secondary
    'accent': '#9B59B6',      # Purple for accents
    'neutral': '#2C3E50',     # Dark gray for text/lines
    'background': '#FAFAFA',  # Light gray background
    'grid': '#CCCCCC'         # Light gray for grids/borders
}
plt.style.use('default')
sns.set_palette("husl")

def load_all_metrics(logs_dir):
    """Load all metrics.json files from subdirectories"""
    metrics_data = []
    
    for subdir in Path(logs_dir).iterdir():
        if subdir.is_dir():
            metrics_file = subdir / 'metrics.json'
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract challenge number from benchmark_name
                    challenge_match = re.search(r'XBOW (\d+)', data['benchmark_name'])
                    if challenge_match:
                        data['challenge_number'] = int(challenge_match.group(1))
                    else:
                        data['challenge_number'] = 0
                    
                    metrics_data.append(data)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error loading {metrics_file}: {e}")
    
    return sorted(metrics_data, key=lambda x: x.get('challenge_number', 0))

def generate_latex_table(data):
    """Generate LaTeX summary table with booktabs"""
    
    # Calculate summary statistics
    df = pd.DataFrame(data)
    
    # Basic statistics
    total_challenges = len(df)
    successful_challenges = len(df[df['flags'].apply(lambda x: x.get('found', False))])
    success_rate = successful_challenges / total_challenges * 100 if total_challenges > 0 else 0
    
    # Time statistics  
    times = df['total_time_seconds']
    avg_time = times.mean()
    median_time = times.median()
    max_time = times.max()
    min_time = times.min()
    
    # Token statistics
    total_input_tokens = df['input_tokens'].sum()
    total_output_tokens = df['output_tokens'].sum()
    total_cached_tokens = df['cached_tokens'].sum()
    total_reasoning_tokens = df['reasoning_tokens'].sum()
    total_tokens = df['total_tokens'].sum()
    
    # Cost statistics
    total_cost = df['costs'].apply(lambda x: x['total_cost']).sum()
    avg_cost_per_challenge = total_cost / total_challenges if total_challenges > 0 else 0
    
    # Tool usage statistics
    total_commands = sum([sum(x['tool_calls'].values()) for x in data])
    avg_commands_per_challenge = total_commands / total_challenges if total_challenges > 0 else 0
    
    latex_table = f"""
\\begin{{table*}}[t]
\\centering
\\caption{{XBOW Challenge Analysis Summary}}
\\label{{tab:xbow_summary}}
\\begin{{tabular}}{{@{{}}lc@{{\\hspace{{2cm}}}}lc@{{}}}}
\\toprule
\\textbf{{Metric}} & \\textbf{{Value}} & \\textbf{{Metric}} & \\textbf{{Value}} \\\\
\\midrule
Total Challenges & {total_challenges} & Success Rate & {success_rate:.1f}\\% \\\\
Successful Challenges & {successful_challenges} & Failed Challenges & {total_challenges - successful_challenges} \\\\
\\midrule
Avg. Solve Time & {avg_time:.1f}s & Median Solve Time & {median_time:.1f}s \\\\
Min Solve Time & {min_time:.1f}s & Max Solve Time & {max_time:.1f}s \\\\
\\midrule
Total Input Tokens & {total_input_tokens:,} & Total Output Tokens & {total_output_tokens:,} \\\\
Total Cached Tokens & {total_cached_tokens:,} & Total Reasoning Tokens & {total_reasoning_tokens:,} \\\\
\\midrule
Total Cost & \\${total_cost:.3f} & Avg. Cost per Challenge & \\${avg_cost_per_challenge:.3f} \\\\
Total Commands & {total_commands} & Avg. Commands per Challenge & {avg_commands_per_challenge:.1f} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table*}}
"""
    
    return latex_table

def plot_time_cdf(data, output_dir):
    """Generate CDF of total challenge times"""
    times = [x['total_time_seconds'] for x in data]
    times_sorted = np.sort(times)
    n = len(times_sorted)
    y = np.arange(1, n + 1) / n * 100
    
    # Separate solved vs unsolved challenges
    solved_times = []
    unsolved_times = []
    for challenge in data:
        time = challenge['total_time_seconds']
        if challenge['flags']['found']:
            solved_times.append(time)
        else:
            unsolved_times.append(time)
    
    plt.figure(figsize=(12, 7), facecolor='white')
    plt.gca().set_facecolor(COLORS['background'])
    
    # Use unified color scheme
    solved_color = COLORS['solved']
    failed_color = COLORS['failed']
    line_color = COLORS['neutral']
    
    # Plot all times with improved styling
    plt.plot(times_sorted, y, linewidth=4, marker='o', markersize=5, color=line_color, 
             label='All Challenges', markerfacecolor='white', markeredgewidth=2, 
             markeredgecolor=line_color, alpha=0.9)
    
    # Add markers for solved vs unsolved with beautiful colors
    if solved_times:
        solved_times_sorted = np.sort(solved_times)
        solved_y = np.arange(1, len(solved_times_sorted) + 1) / len(solved_times_sorted) * 100
        plt.scatter(solved_times, [np.interp(t, times_sorted, y) for t in solved_times], 
                   color=solved_color, s=80, alpha=0.9, label='Solved', zorder=6, 
                   edgecolors='white', linewidth=1.5, marker='o')
    
    if unsolved_times:
        plt.scatter(unsolved_times, [np.interp(t, times_sorted, y) for t in unsolved_times], 
                   color=failed_color, s=80, alpha=0.9, label='Unsolved', zorder=6,
                   edgecolors='white', linewidth=1.5, marker='X')
    
    plt.xlabel('Total Time Spent on Challenge (seconds)', fontsize=20, fontweight='bold')
    plt.ylabel('Cumulative Percentage (%)', fontsize=20, fontweight='bold')
    plt.title('Cumulative Distribution of Challenge Completion Times', fontsize=22, fontweight='bold', pad=20)
    plt.tick_params(axis='both', which='major', labelsize=18)
    plt.grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    
    # Remove top and right spines for cleaner look
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    plt.xlim(0, max(times_sorted) * 1.05)
    plt.ylim(0, 100)
    
    # Add statistics with separate medians for solved/unsolved - beautiful styling
    median_time_all = np.median(times)
    plt.axvline(median_time_all, color=line_color, linestyle='--', alpha=0.8, linewidth=3,
                label=f'Overall Median: {median_time_all:.1f}s')
    
    if solved_times:
        median_solved = np.median(solved_times)
        plt.axvline(median_solved, color=solved_color, linestyle='--', alpha=0.8, linewidth=3,
                    label=f'Solved Median: {median_solved:.1f}s')
    
    if unsolved_times:
        median_unsolved = np.median(unsolved_times)
        plt.axvline(median_unsolved, color=failed_color, linestyle='--', alpha=0.8, linewidth=3,
                    label=f'Unsolved Median: {median_unsolved:.1f}s')
    
    plt.legend(fontsize=14, frameon=True, fancybox=True, shadow=True, 
               facecolor='white', edgecolor=COLORS['grid'])
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/time_cdf.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/time_cdf.pdf', bbox_inches='tight', facecolor='white')
    plt.close()

def plot_token_cdfs(data, output_dir):
    """Generate multiple CDFs for different token types"""
    token_types = {
        'Input Tokens': [x['input_tokens'] for x in data],
        'Output Tokens': [x['output_tokens'] for x in data],  
        'Cached Tokens': [x['cached_tokens'] for x in data],
        'Reasoning Tokens': [x['reasoning_tokens'] for x in data],
        'Total Tokens': [x['total_tokens'] for x in data]
    }
    
    plt.figure(figsize=(14, 8), facecolor='white')
    plt.gca().set_facecolor(COLORS['background'])
    
    # Unified color palette
    colors = [COLORS['primary'], COLORS['failed'], COLORS['secondary'], COLORS['solved'], COLORS['accent']]
    markers = ['o', 's', '^', 'D', 'v']
    
    for i, (label, tokens) in enumerate(token_types.items()):
        tokens_sorted = np.sort(tokens)
        n = len(tokens_sorted)
        y = np.arange(1, n + 1) / n * 100
        plt.plot(tokens_sorted, y, linewidth=4, label=label, marker=markers[i], markersize=4,
                color=colors[i % len(colors)], markerfacecolor='white', 
                markeredgewidth=2, markeredgecolor=colors[i % len(colors)], alpha=0.9)
    
    plt.xlabel('Number of Tokens', fontsize=20, fontweight='bold')
    plt.ylabel('Cumulative Percentage (%)', fontsize=20, fontweight='bold')
    plt.title('Cumulative Distribution of Token Usage by Type', fontsize=22, fontweight='bold', pad=20)
    plt.tick_params(axis='both', which='major', labelsize=18)
    plt.tick_params(axis='both', which='minor', labelsize=16)
    plt.legend(fontsize=14, frameon=True, fancybox=True, shadow=True, 
               facecolor='white', edgecolor=COLORS['grid'])
    plt.grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    
    # Remove top and right spines for cleaner look
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    plt.xscale('log')
    plt.xlim(100, max(token_types['Total Tokens']) * 1.5)
    plt.ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/token_cdfs.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/token_cdfs.pdf', bbox_inches='tight', facecolor='white')
    plt.close()

def plot_cost_analysis(data, output_dir):
    """Generate cost breakdown analysis"""
    cost_types = {
        'Regular Input Cost': [x['costs']['regular_input_cost'] for x in data],
        'Cached Input Cost': [x['costs']['cached_input_cost'] for x in data],
        'Output Cost': [x['costs']['output_cost'] for x in data],
        'Total Cost': [x['costs']['total_cost'] for x in data]
    }
    
    # Separate solved vs unsolved costs
    solved_costs = []
    unsolved_costs = []
    for challenge in data:
        cost = challenge['costs']['total_cost']
        if challenge['flags']['found']:
            solved_costs.append(cost)
        else:
            unsolved_costs.append(cost)
    
    # Create subplot for different cost visualizations with beautiful styling
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor='white')
    fig.patch.set_facecolor('white')
    
    # Use unified color scheme
    solved_color = COLORS['solved']
    failed_color = COLORS['failed']
    line_color = COLORS['neutral']
    
    for ax in axes.flat:
        ax.set_facecolor(COLORS['background'])
        # Remove top and right spines for cleaner look
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(COLORS['grid'])
        ax.spines['bottom'].set_color(COLORS['grid'])
    
    # CDF of total costs with solved/unsolved distinction
    costs_sorted = np.sort(cost_types['Total Cost'])
    n = len(costs_sorted)
    y = np.arange(1, n + 1) / n * 100
    axes[0].plot(costs_sorted, y, linewidth=4, marker='o', markersize=5, color=line_color, 
                 label='All Challenges', markerfacecolor='white', markeredgewidth=2,
                 markeredgecolor=line_color, alpha=0.9)
    
    # Add markers for solved vs unsolved with beautiful colors
    if solved_costs:
        axes[0].scatter(solved_costs, [np.interp(c, costs_sorted, y) for c in solved_costs], 
                       color=solved_color, s=80, alpha=0.9, label='Solved', zorder=6,
                       edgecolors='white', linewidth=1.5, marker='o')
    
    if unsolved_costs:
        axes[0].scatter(unsolved_costs, [np.interp(c, costs_sorted, y) for c in unsolved_costs], 
                       color=failed_color, s=80, alpha=0.9, label='Unsolved', zorder=6,
                       edgecolors='white', linewidth=1.5, marker='X')
    
    axes[0].set_xlabel('Total Cost (USD)', fontsize=16, fontweight='bold')
    axes[0].set_ylabel('Cumulative Percentage (%)', fontsize=16, fontweight='bold')
    axes[0].set_title('CDF of Total Costs', fontsize=18, fontweight='bold', pad=20)
    axes[0].grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    
    # Add medians for costs with beautiful styling
    median_cost_all = np.median(cost_types['Total Cost'])
    axes[0].axvline(median_cost_all, color=line_color, linestyle='--', alpha=0.8, linewidth=3,
                    label=f'Overall Median: ${median_cost_all:.3f}')
    
    if solved_costs:
        median_solved_cost = np.median(solved_costs)
        axes[0].axvline(median_solved_cost, color=solved_color, linestyle='--', alpha=0.8, linewidth=3,
                        label=f'Solved Median: ${median_solved_cost:.3f}')
    
    if unsolved_costs:
        median_unsolved_cost = np.median(unsolved_costs)
        axes[0].axvline(median_unsolved_cost, color=failed_color, linestyle='--', alpha=0.8, linewidth=3,
                        label=f'Unsolved Median: ${median_unsolved_cost:.3f}')
    
    axes[0].legend(fontsize=14, frameon=True, fancybox=True, shadow=True, 
                   facecolor='white', edgecolor=COLORS['grid'])
    
    # Cost breakdown by challenge
    challenges = [f"Ch{x['challenge_number']}" for x in data]
    df_costs = pd.DataFrame({
        'Challenge': challenges,
        'Regular Input': cost_types['Regular Input Cost'],
        'Cached Input': cost_types['Cached Input Cost'], 
        'Output': cost_types['Output Cost']
    })
    
    # Stacked bar chart with unified colors
    beautiful_bar_colors = [COLORS['primary'], COLORS['secondary'], COLORS['failed']]
    df_costs.set_index('Challenge')[['Regular Input', 'Cached Input', 'Output']].plot(
        kind='bar', stacked=True, ax=axes[1], color=beautiful_bar_colors, alpha=0.9, 
        width=0.8, edgecolor='white', linewidth=0.5)
    axes[1].set_title('Cost Breakdown by Challenge', fontsize=18, fontweight='bold', pad=20)
    axes[1].set_ylabel('Cost (USD)', fontsize=16, fontweight='bold')
    axes[1].grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    
    # Fix x-axis labels for 104 challenges - show every 10th label
    num_challenges = len(challenges)
    tick_positions = range(0, num_challenges, max(1, num_challenges // 10))
    axes[1].set_xticks(tick_positions)
    axes[1].set_xticklabels([challenges[i] for i in tick_positions], rotation=45, fontsize=14)
    axes[1].tick_params(axis='y', labelsize=14)
    
    # Style the legend
    axes[1].legend(fontsize=12, frameon=True, fancybox=True, shadow=True, 
                   facecolor='white', edgecolor=COLORS['grid'])
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cost_analysis.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/cost_analysis.pdf', bbox_inches='tight', facecolor='white')
    plt.close()

def plot_tool_usage(data, output_dir):
    """Generate tool usage analysis (excluding e2b labels)"""
    all_tools = defaultdict(list)
    
    for challenge in data:
        challenge_num = challenge['challenge_number']
        total_calls = 0
        for tool, count in challenge['tool_calls'].items():
            # Remove e2b prefix for cleaner labels
            clean_tool = tool.replace('e2b_', '')
            all_tools[clean_tool].append(count)
            total_calls += count
        all_tools['total'].append(total_calls)
    
    # Create subplots for different views with beautiful styling
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor='white')
    fig.patch.set_facecolor('white')
    
    # Use unified color scheme
    primary_color = COLORS['primary']
    secondary_color = COLORS['failed']
    
    for ax in axes.flat:
        ax.set_facecolor(COLORS['background'])
        # Remove top and right spines for cleaner look
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(COLORS['grid'])
        ax.spines['bottom'].set_color(COLORS['grid'])
    
    # Box plot of tool usage
    tool_data = []
    tool_labels = []
    for tool, counts in all_tools.items():
        if tool != 'total':
            tool_data.append(counts)
            tool_labels.append(tool.replace('_', ' ').title())
    
    bp = axes[0].boxplot(tool_data, labels=tool_labels, patch_artist=True,
                        boxprops=dict(facecolor=primary_color, alpha=0.8, linewidth=2),
                        medianprops=dict(color='#2C3E50', linewidth=3),
                        whiskerprops=dict(linewidth=2, color='#2C3E50'),
                        capprops=dict(linewidth=2, color='#2C3E50'),
                        flierprops=dict(marker='o', markerfacecolor=secondary_color, markersize=6, alpha=0.8))
    axes[0].set_title('Distribution of Tool Usage per Challenge', fontsize=18, fontweight='bold', pad=20)
    axes[0].set_ylabel('Number of Calls', fontsize=16, fontweight='bold')
    axes[0].tick_params(axis='x', rotation=45, labelsize=14)
    axes[0].tick_params(axis='y', labelsize=14)
    axes[0].grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    
    # Total tool calls per challenge with beautiful styling
    challenges = [f"Ch{x['challenge_number']}" for x in data]
    bars = axes[1].bar(challenges, all_tools['total'], color=primary_color, alpha=0.9, 
                      edgecolor='white', linewidth=1, width=0.8)
    # Add subtle gradient effect with beautiful edge color
    for bar in bars:
        bar.set_edgecolor('#45B7A8')
    axes[1].set_title('Total Tool Calls per Challenge', fontsize=18, fontweight='bold', pad=20)
    axes[1].set_ylabel('Total Calls', fontsize=16, fontweight='bold')
    axes[1].grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--', linewidth=1)
    # Fix x-axis labels for 104 challenges - show every 10th label
    num_challenges = len(challenges)
    tick_positions = range(0, num_challenges, max(1, num_challenges // 10))
    axes[1].set_xticks(tick_positions)
    axes[1].set_xticklabels([challenges[i] for i in tick_positions], rotation=45, fontsize=14)
    axes[1].tick_params(axis='y', labelsize=16)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/tool_usage_analysis.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/tool_usage_analysis.pdf', bbox_inches='tight', facecolor='white')
    plt.close()

def analyze_command_usage(data, output_dir):
    """Analyze command usage patterns"""
    all_commands = Counter()
    command_by_challenge = defaultdict(dict)
    
    for challenge in data:
        challenge_num = challenge['challenge_number']
        for cmd, count in challenge['command_usage'].items():
            all_commands[cmd] += count
            command_by_challenge[challenge_num][cmd] = count
    
    # Create command usage table (LaTeX)
    latex_command_table = """
\\begin{table}[h]
\\centering
\\caption{Command Usage Summary}
\\label{tab:command_usage}
\\begin{tabular}{@{}lcc@{}}
\\toprule
\\textbf{Command} & \\textbf{Total Usage} & \\textbf{Avg per Challenge} \\\\
\\midrule
"""
    
    total_challenges = len(data)
    for cmd, total_count in all_commands.most_common():
        avg_usage = total_count / total_challenges
        latex_command_table += f"{cmd} & {total_count} & {avg_usage:.1f} \\\\\n"
    
    latex_command_table += """\\bottomrule
\\end{tabular}
\\end{table}
"""
    
    # Create command usage visualization with beautiful styling
    fig, ax = plt.subplots(1, 1, figsize=(16, 8), facecolor='white')
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['background'])
    
    # Command usage per challenge heatmap
    all_cmd_names = sorted(all_commands.keys())
    cmd_matrix = []
    challenge_labels = []
    
    for challenge in sorted(data, key=lambda x: x['challenge_number']):
        challenge_labels.append(f"Ch{challenge['challenge_number']}")
        row = []
        for cmd in all_cmd_names:
            count = challenge['command_usage'].get(cmd, 0)
            row.append(count)
        cmd_matrix.append(row)
    
    # Use a bright, beautiful colormap with white for zero values
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.colors as mcolors
    
    # Create custom colormap: white for 0, yellow at 1, then to dark blue at highest
    # Using yellow -> orange -> red -> purple -> dark blue progression
    colors_list = ['white', '#FFD700', '#FF8C00', '#FF4500', '#8B0000', '#4B0082', '#191970']
    custom_cmap = LinearSegmentedColormap.from_list('custom_bright', colors_list, N=256)
    
    im = ax.imshow(cmd_matrix, cmap=custom_cmap, aspect='auto', interpolation='nearest', alpha=0.9)
    
    # Add subtle grid lines for better readability
    for i in range(len(challenge_labels)):
        ax.axhline(i - 0.5, color='white', linewidth=0.8, alpha=0.3)
    for j in range(len(all_cmd_names)):
        ax.axvline(j - 0.5, color='white', linewidth=0.8, alpha=0.3)
        
    ax.set_title('Command Usage by Challenge', fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Command', fontsize=16, fontweight='bold')
    ax.set_ylabel('Challenge', fontsize=16, fontweight='bold')
    
    # Fix axis labels for better readability
    ax.set_xticks(range(len(all_cmd_names)))
    ax.set_xticklabels(all_cmd_names, rotation=45, ha='right', fontsize=12)
    
    # For y-axis, show every 5th challenge to avoid crowding
    y_tick_positions = range(0, len(challenge_labels), max(1, len(challenge_labels) // 20))
    ax.set_yticks(y_tick_positions)
    ax.set_yticklabels([challenge_labels[i] for i in y_tick_positions], fontsize=12)
    
    # Beautiful colorbar with better styling
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label('Command Usage Count', fontsize=14, fontweight='bold')
    cbar.ax.tick_params(labelsize=12)
    
    # Remove top and right spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/command_usage_analysis.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/command_usage_analysis.pdf', bbox_inches='tight', facecolor='white')
    plt.close()
    
    return latex_command_table

def extract_challenge_types(benchmarks_dir="/Users/dachtuer/pentesting-agents/validation-benchmarks/benchmarks"):
    """Extract vulnerability types and categories from challenge README files"""
    challenge_types = {}
    
    for challenge_dir in sorted(os.listdir(benchmarks_dir)):
        if challenge_dir.startswith('XBEN-'):
            # Extract challenge number from XBEN-XXX-24
            challenge_num = int(challenge_dir.split('-')[1])
            readme_path = os.path.join(benchmarks_dir, challenge_dir, 'README.md')
            
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract ALL vulnerability types and categories using regex
                    type_matches = re.findall(r'- \*\*Type:\*\* (.+)', content)
                    category_matches = re.findall(r'- \*\*Category:\*\* (.+)', content)
                    
                    # Clean and process matches
                    types = [t.strip() for t in type_matches if t.strip()]
                    categories = [c.strip() for c in category_matches if c.strip()]
                    
                    # For challenges with multiple types, create a combined label
                    if len(types) > 1:
                        # Use the most specific type or combine them
                        primary_type = types[-1]  # Often the most specific is last
                        vuln_type = f"{primary_type} (Multi-vuln)"
                    elif types:
                        vuln_type = types[0]
                    else:
                        vuln_type = 'Unknown'
                    
                    # Use category for consistency
                    vuln_category = categories[0] if categories else 'Unknown'
                    
                    challenge_types[challenge_num] = {
                        'type': vuln_type,
                        'category': vuln_category,
                        'all_types': types,
                        'all_categories': categories
                    }
                    
                except Exception as e:
                    print(f"Error reading {readme_path}: {e}")
                    challenge_types[challenge_num] = {'type': 'Unknown', 'category': 'Unknown', 'all_types': [], 'all_categories': []}
            else:
                challenge_types[challenge_num] = {'type': 'Unknown', 'category': 'Unknown', 'all_types': [], 'all_categories': []}
    
    return challenge_types

def plot_sankey_analysis(data, output_dir):
    """Create Sankey diagram showing benchmark outcomes and challenge types"""
    try:
        import plotly.graph_objects as go
        from plotly.offline import plot
    except ImportError:
        print("Plotly not available for Sankey diagrams. Installing...")
        import subprocess
        subprocess.run(['pip', 'install', 'plotly', 'kaleido'], check=True)
        import plotly.graph_objects as go
        from plotly.offline import plot
    
    # Extract challenge types
    challenge_types = extract_challenge_types()
    
    # Prepare data for Sankey
    sources = []
    targets = []
    values = []
    labels = []
    node_colors = []
    
    # Count outcomes first
    succeeded_count = sum(1 for c in data if c['flags']['found'])
    failed_count = len(data) - succeeded_count
    
    # Create nodes: All Benchmarks → Success/Failure → Challenge Types
    labels.append("All Benchmarks (104)")
    labels.append(f"Succeeded ({succeeded_count})")
    labels.append(f"Failed ({failed_count})")
    
    # Add flows from All Benchmarks to outcomes
    sources.extend([0, 0])  # From "All Benchmarks"
    targets.extend([1, 2])  # To "Succeeded", "Failed"
    values.extend([succeeded_count, failed_count])
    
    # Collect challenge types for succeeded and failed
    succeeded_types = defaultdict(int)
    failed_types = defaultdict(int)
    
    for challenge in data:
        challenge_num = challenge['challenge_number']
        challenge_info = challenge_types.get(challenge_num, {'type': 'Unknown', 'category': 'Unknown'})
        
        # For injection category, use specific injection type for better granularity
        if challenge_info['category'] == 'Injection':
            # Look for specific injection types in all_types
            specific_injection = None
            for t in challenge_info.get('all_types', []):
                if any(keyword in t.lower() for keyword in ['xss', 'cross-site scripting']):
                    specific_injection = 'Cross-Site Scripting (XSS)'
                    break
                elif 'sql injection' in t.lower() or 'sqli' in t.lower():
                    if 'blind' in t.lower():
                        specific_injection = 'Blind SQL Injection'
                    else:
                        specific_injection = 'SQL Injection'
                    break
                elif 'no-sql' in t.lower() or 'nosql' in t.lower():
                    specific_injection = 'NoSQL Injection'
                    break
                elif 'command injection' in t.lower():
                    specific_injection = 'Command Injection'
                    break
                elif 'template injection' in t.lower() or 'ssti' in t.lower():
                    specific_injection = 'Server-Side Template Injection (SSTI)'
                    break
            
            vuln_type = specific_injection if specific_injection else challenge_info['category']
        else:
            vuln_type = challenge_info['category']
        
        if challenge['flags']['found']:
            succeeded_types[vuln_type] += 1
        else:
            failed_types[vuln_type] += 1
    
    # Add type nodes and flows
    type_start_idx = len(labels)
    all_types = set(list(succeeded_types.keys()) + list(failed_types.keys()))
    
    for vuln_type in sorted(all_types):
        total_count = succeeded_types[vuln_type] + failed_types[vuln_type]
        labels.append(f"{vuln_type} ({total_count})")
        type_idx = len(labels) - 1
        
        # Flow from Succeeded to this type
        if succeeded_types[vuln_type] > 0:
            sources.append(1)  # From "Succeeded"
            targets.append(type_idx)
            values.append(succeeded_types[vuln_type])
        
        # Flow from Failed to this type
        if failed_types[vuln_type] > 0:
            sources.append(2)  # From "Failed"
            targets.append(type_idx)
            values.append(failed_types[vuln_type])
    
    # Create node colors
    node_colors = [
        COLORS['neutral'],     # All Benchmarks
        COLORS['solved'],      # Succeeded
        COLORS['failed'],      # Failed
    ] + [COLORS['primary']] * len(all_types)  # All types in blue
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=4,           # Reduced padding to decrease spacing between columns
            thickness=15,    # Standard thickness
            line=dict(color="black", width=0.5),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            label=[f"{v}" for v in values],  # Add flow labels with values
            color=['rgba(39, 174, 96, 0.6)' if targets[i] < 3 and sources[i] == 1 
                   else 'rgba(231, 76, 60, 0.6)' if targets[i] < 3 and sources[i] == 2
                   else 'rgba(52, 152, 219, 0.4)' for i in range(len(sources))]
        ))])
    
    fig.update_layout(
        title_text="XBOW Challenge Analysis: Outcomes and Vulnerability Types",
        title_x=0.5,
        title_font_size=18,  # Increased from 14 to 18
        font_size=14,        # Increased from 9 to 14
        width=600,           # Single column width
        height=650,          # Taller to accommodate all labels
        margin=dict(l=15, r=15, t=50, b=50),  # Balanced margins with more bottom space
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    # Save as HTML and PNG
    fig.write_html(f'{output_dir}/sankey_analysis.html')
    fig.write_image(f'{output_dir}/sankey_analysis.png', width=600, height=650, scale=3)  # Match layout height
    fig.write_image(f'{output_dir}/sankey_analysis.pdf', width=600, height=650)
    
    # Print summary
    print(f"\nSankey Analysis Summary:")
    print(f"Total Challenges: {len(data)}")
    print(f"Succeeded: {succeeded_count}, Failed: {failed_count}")
    print(f"Unique Vulnerability Types: {len(all_types)}")
    print(f"Top Succeeded Types: {sorted(succeeded_types.items(), key=lambda x: x[1], reverse=True)[:3]}")
    print(f"Top Failed Types: {sorted(failed_types.items(), key=lambda x: x[1], reverse=True)[:3]}")

def plot_success_correlation(data, output_dir):
    """Analyze correlation between success rate and resource usage with better visualization for binary outcomes"""
    from scipy import stats
    
    # Extract metrics for each challenge
    times_solved = []
    times_failed = []
    costs_solved = []
    costs_failed = []
    tokens_solved = []
    tokens_failed = []
    tools_solved = []
    tools_failed = []
    
    all_times = []
    all_costs = []
    all_tokens = []
    all_tools = []
    success_flags = []
    
    for challenge in data:
        time_val = challenge['total_time_seconds']
        cost_val = challenge['costs']['total_cost']
        token_val = challenge['total_tokens']
        tool_val = sum(challenge['tool_calls'].values())
        
        success = challenge['flags']['found']
        
        # Store for correlation calculation
        all_times.append(time_val)
        all_costs.append(cost_val)
        all_tokens.append(token_val)
        all_tools.append(tool_val)
        success_flags.append(1 if success else 0)
        
        # Separate by success/failure for violin plots
        if success:
            times_solved.append(time_val)
            costs_solved.append(cost_val)
            tokens_solved.append(token_val)
            tools_solved.append(tool_val)
        else:
            times_failed.append(time_val)
            costs_failed.append(cost_val)
            tokens_failed.append(token_val)
            tools_failed.append(tool_val)
    
    # Create 2x2 subplot layout with better styling
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), facecolor='white')
    fig.patch.set_facecolor('white')
    
    # Set a beautiful background color
    for ax in axes.flat:
        ax.set_facecolor(COLORS['background'])
    
    # Use unified color scheme
    failed_color = COLORS['failed']
    solved_color = COLORS['solved']
    
    
    # Plot 1: Time distribution by success/failure (side-by-side, not symmetrical)
    # Use split violins to get true side-by-side effect
    positions = [0, 1]
    data_time = [times_failed, times_solved]
    
    vp1 = axes[0,0].violinplot(data_time, positions=positions, widths=0.8,
                               showmeans=True, showmedians=True, showextrema=True)
    
    # Manually create side-by-side effect by modifying violin paths
    for i, pc in enumerate(vp1['bodies']):
        if i == 0:  # Failed (left side)
            pc.set_facecolor(failed_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#C0392B')
            # Keep only left half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] > positions[i], positions[i], vertices[:, 0])
        else:  # Solved (right side)
            pc.set_facecolor(solved_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#229954')
            # Keep only right half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] < positions[i], positions[i], vertices[:, 0])
        pc.set_linewidth(2)
    
    # Style statistics
    for partname in ('cmedians', 'cmeans'):
        if partname in vp1:
            vp1[partname].set_colors([COLORS['neutral'], COLORS['neutral']])
            vp1[partname].set_linewidth(3)
    for partname in ('cbars', 'cmins', 'cmaxes'):
        if partname in vp1:
            vp1[partname].set_color(COLORS['neutral'])
            vp1[partname].set_linewidth(2)
    
    axes[0,0].set_xticks([0, 1])
    axes[0,0].set_xticklabels(['Failed', 'Solved'], fontsize=22, fontweight='bold')
    axes[0,0].set_ylabel('Total Time (seconds)', fontsize=22, fontweight='bold')
    axes[0,0].set_title('Time Distribution by Outcome', fontsize=24, fontweight='bold', pad=20)
    axes[0,0].grid(True, alpha=0.3, linestyle='--', linewidth=1)
    axes[0,0].tick_params(axis='y', labelsize=20)
    axes[0,0].spines['top'].set_visible(False)
    axes[0,0].spines['right'].set_visible(False)
    axes[0,0].spines['left'].set_color('#CCCCCC')
    axes[0,0].spines['bottom'].set_color('#CCCCCC')
    
    # Add correlation info with better styling
    corr_time, p_time = stats.pearsonr(all_times, success_flags)
    axes[0,0].text(0.95, 0.95, f'r = {corr_time:.3f}', 
                   transform=axes[0,0].transAxes, fontsize=18, fontweight='bold',
                   verticalalignment='top', horizontalalignment='right', color=COLORS['neutral'],
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor=COLORS['grid']))
    
    # Plot 2: Cost distribution by success/failure (side-by-side)
    positions = [0, 1]
    data_cost = [costs_failed, costs_solved]
    
    vp2 = axes[0,1].violinplot(data_cost, positions=positions, widths=0.8,
                               showmeans=True, showmedians=True, showextrema=True)
    
    # Manually create side-by-side effect by modifying violin paths
    for i, pc in enumerate(vp2['bodies']):
        if i == 0:  # Failed (left side)
            pc.set_facecolor(failed_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#C0392B')
            # Keep only left half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] > positions[i], positions[i], vertices[:, 0])
        else:  # Solved (right side)
            pc.set_facecolor(solved_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#229954')
            # Keep only right half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] < positions[i], positions[i], vertices[:, 0])
        pc.set_linewidth(2)
    
    # Style statistics
    for partname in ('cmedians', 'cmeans'):
        if partname in vp2:
            vp2[partname].set_colors([COLORS['neutral'], COLORS['neutral']])
            vp2[partname].set_linewidth(3)
    for partname in ('cbars', 'cmins', 'cmaxes'):
        if partname in vp2:
            vp2[partname].set_color(COLORS['neutral'])
            vp2[partname].set_linewidth(2)
    
    axes[0,1].set_xticks([0, 1])
    axes[0,1].set_xticklabels(['Failed', 'Solved'], fontsize=22, fontweight='bold')
    axes[0,1].set_ylabel('Total Cost (USD)', fontsize=22, fontweight='bold')
    axes[0,1].set_title('Cost Distribution by Outcome', fontsize=24, fontweight='bold', pad=20)
    axes[0,1].grid(True, alpha=0.3, linestyle='--', linewidth=1)
    axes[0,1].tick_params(axis='y', labelsize=20)
    axes[0,1].spines['top'].set_visible(False)
    axes[0,1].spines['right'].set_visible(False)
    axes[0,1].spines['left'].set_color('#CCCCCC')
    axes[0,1].spines['bottom'].set_color('#CCCCCC')
    
    corr_cost, p_cost = stats.pearsonr(all_costs, success_flags)
    axes[0,1].text(0.95, 0.95, f'r = {corr_cost:.3f}', 
                   transform=axes[0,1].transAxes, fontsize=18, fontweight='bold',
                   verticalalignment='top', horizontalalignment='right', color=COLORS['neutral'],
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor=COLORS['grid']))
    
    # Plot 3: Token distribution by success/failure (side-by-side)
    positions = [0, 1]
    data_tokens = [tokens_failed, tokens_solved]
    
    vp3 = axes[1,0].violinplot(data_tokens, positions=positions, widths=0.8,
                               showmeans=True, showmedians=True, showextrema=True)
    
    # Manually create side-by-side effect by modifying violin paths
    for i, pc in enumerate(vp3['bodies']):
        if i == 0:  # Failed (left side)
            pc.set_facecolor(failed_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#C0392B')
            # Keep only left half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] > positions[i], positions[i], vertices[:, 0])
        else:  # Solved (right side)
            pc.set_facecolor(solved_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#229954')
            # Keep only right half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] < positions[i], positions[i], vertices[:, 0])
        pc.set_linewidth(2)
    
    # Style statistics
    for partname in ('cmedians', 'cmeans'):
        if partname in vp3:
            vp3[partname].set_colors([COLORS['neutral'], COLORS['neutral']])
            vp3[partname].set_linewidth(3)
    for partname in ('cbars', 'cmins', 'cmaxes'):
        if partname in vp3:
            vp3[partname].set_color(COLORS['neutral'])
            vp3[partname].set_linewidth(2)
    
    axes[1,0].set_xticks([0, 1])
    axes[1,0].set_xticklabels(['Failed', 'Solved'], fontsize=22, fontweight='bold')
    axes[1,0].set_ylabel('Total Tokens', fontsize=22, fontweight='bold')
    axes[1,0].set_title('Token Distribution by Outcome', fontsize=24, fontweight='bold', pad=20)
    axes[1,0].grid(True, alpha=0.3, linestyle='--', linewidth=1)
    axes[1,0].set_yscale('log')
    axes[1,0].tick_params(axis='y', labelsize=20)
    axes[1,0].spines['top'].set_visible(False)
    axes[1,0].spines['right'].set_visible(False)
    axes[1,0].spines['left'].set_color('#CCCCCC')
    axes[1,0].spines['bottom'].set_color('#CCCCCC')
    
    corr_tokens, p_tokens = stats.pearsonr(all_tokens, success_flags)
    axes[1,0].text(0.95, 0.95, f'r = {corr_tokens:.3f}', 
                   transform=axes[1,0].transAxes, fontsize=18, fontweight='bold',
                   verticalalignment='top', horizontalalignment='right', color=COLORS['neutral'],
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor=COLORS['grid']))
    
    # Plot 4: Tool distribution by success/failure (side-by-side)
    positions = [0, 1]
    data_tools = [tools_failed, tools_solved]
    
    vp4 = axes[1,1].violinplot(data_tools, positions=positions, widths=0.8,
                               showmeans=True, showmedians=True, showextrema=True)
    
    # Manually create side-by-side effect by modifying violin paths
    for i, pc in enumerate(vp4['bodies']):
        if i == 0:  # Failed (left side)
            pc.set_facecolor(failed_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#C0392B')
            # Keep only left half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] > positions[i], positions[i], vertices[:, 0])
        else:  # Solved (right side)
            pc.set_facecolor(solved_color)
            pc.set_alpha(0.8)
            pc.set_edgecolor('#229954')
            # Keep only right half of violin
            vertices = pc.get_paths()[0].vertices
            vertices[:, 0] = np.where(vertices[:, 0] < positions[i], positions[i], vertices[:, 0])
        pc.set_linewidth(2)
    
    # Style statistics
    for partname in ('cmedians', 'cmeans'):
        if partname in vp4:
            vp4[partname].set_colors([COLORS['neutral'], COLORS['neutral']])
            vp4[partname].set_linewidth(3)
    for partname in ('cbars', 'cmins', 'cmaxes'):
        if partname in vp4:
            vp4[partname].set_color(COLORS['neutral'])
            vp4[partname].set_linewidth(2)
    
    axes[1,1].set_xticks([0, 1])
    axes[1,1].set_xticklabels(['Failed', 'Solved'], fontsize=22, fontweight='bold')
    axes[1,1].set_ylabel('Total Tool Calls', fontsize=22, fontweight='bold')
    axes[1,1].set_title('Tool Usage Distribution by Outcome', fontsize=24, fontweight='bold', pad=20)
    axes[1,1].grid(True, alpha=0.3, linestyle='--', linewidth=1)
    axes[1,1].tick_params(axis='y', labelsize=20)
    axes[1,1].spines['top'].set_visible(False)
    axes[1,1].spines['right'].set_visible(False)
    axes[1,1].spines['left'].set_color('#CCCCCC')
    axes[1,1].spines['bottom'].set_color('#CCCCCC')
    
    corr_tools, p_tools = stats.pearsonr(all_tools, success_flags)
    axes[1,1].text(0.95, 0.95, f'r = {corr_tools:.3f}', 
                   transform=axes[1,1].transAxes, fontsize=18, fontweight='bold',
                   verticalalignment='top', horizontalalignment='right', color=COLORS['neutral'],
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor=COLORS['grid']))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/success_correlation.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/success_correlation.pdf', bbox_inches='tight', facecolor='white')
    plt.close()
    
    # Print correlation summary
    print(f"\nCorrelation Analysis:")
    print(f"Time vs Success: r={corr_time:.3f}, p-value={p_time:.3f}")
    print(f"Cost vs Success: r={corr_cost:.3f}, p-value={p_cost:.3f}")
    print(f"Tokens vs Success: r={corr_tokens:.3f}, p-value={p_tokens:.3f}")
    print(f"Tools vs Success: r={corr_tools:.3f}, p-value={p_tools:.3f}")

def main():
    logs_dir = "./ctf-logs"
    output_dir = "./analysis_output"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load all metrics data
    print("Loading metrics data...")
    data = load_all_metrics(logs_dir)
    print(f"Loaded {len(data)} challenge results")
    
    # Generate LaTeX summary table
    print("Generating LaTeX summary table...")
    latex_table = generate_latex_table(data)
    with open(f'{output_dir}/summary_table.tex', 'w') as f:
        f.write(latex_table)
    
    # Generate time CDF
    print("Generating time CDF...")
    plot_time_cdf(data, output_dir)
    
    # Generate token CDFs
    print("Generating token CDFs...")
    plot_token_cdfs(data, output_dir)
    
    # Generate cost analysis
    print("Generating cost analysis...")
    plot_cost_analysis(data, output_dir)
    
    # Generate tool usage analysis
    print("Generating tool usage analysis...")
    plot_tool_usage(data, output_dir)
    
    # Generate command usage analysis
    print("Generating command usage analysis...")
    latex_cmd_table = analyze_command_usage(data, output_dir)
    with open(f'{output_dir}/command_table.tex', 'w') as f:
        f.write(latex_cmd_table)
    
    # Generate success correlation analysis
    print("Generating success correlation analysis...")
    plot_success_correlation(data, output_dir)
    
    # Generate Sankey diagram analysis
    print("Generating Sankey diagram analysis...")
    plot_sankey_analysis(data, output_dir)
    
    print(f"Analysis complete! Results saved to {output_dir}")
    print("\nGenerated files:")
    print("- summary_table.tex (LaTeX summary table)")
    print("- command_table.tex (LaTeX command usage table)")
    print("- time_cdf.png/pdf (Time CDF)")
    print("- token_cdfs.png/pdf (Token usage CDFs)")
    print("- cost_analysis.png/pdf (Cost analysis)")
    print("- tool_usage_analysis.png/pdf (Tool usage analysis)")
    print("- command_usage_analysis.png/pdf (Command usage analysis)")
    print("- success_correlation.png/pdf (Success vs Resource correlation)")
    print("- sankey_analysis.html/png/pdf (Sankey flow diagram)")

if __name__ == "__main__":
    main()
