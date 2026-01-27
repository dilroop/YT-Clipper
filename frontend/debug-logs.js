/**
 * Debug Helper for Split-Screen Logs Panel
 * Load this in browser console to diagnose issues
 */

(function() {
    console.log('🔍 Starting Split-Screen Logs Diagnostic...\n');

    // Check if split-screen manager exists
    if (typeof splitScreenManager === 'undefined') {
        console.error('❌ splitScreenManager not found! Script may not be loaded.');
        return;
    }

    console.log('✅ splitScreenManager found');

    // Check DOM elements
    const elements = {
        'Split Container': document.querySelector('.split-container'),
        'Logs Panel': document.querySelector('.logs-panel'),
        'Logs Panel Content': document.querySelector('.logs-panel-content'),
        'Empty State': document.querySelector('.empty-log-state'),
        'Log Lines': document.querySelectorAll('.log-line'),
        'Toggle Button': document.getElementById('logsToggleBtn')
    };

    console.log('\n📋 DOM Elements Check:');
    for (const [name, element] of Object.entries(elements)) {
        if (name === 'Log Lines') {
            console.log(`  ${element.length > 0 ? '✅' : '⚠️'} ${name}: ${element.length} found`);
        } else {
            console.log(`  ${element ? '✅' : '❌'} ${name}: ${element ? 'Found' : 'Missing'}`);
        }
    }

    // Check activation state
    console.log('\n🔧 Split-Screen State:');
    console.log('  Is Active:', splitScreenManager.isActive);
    console.log('  Line Count:', splitScreenManager.lineCount);
    console.log('  Auto Scroll:', splitScreenManager.autoScroll);

    // Check WebSocket
    if (splitScreenManager.logsWs) {
        const wsStates = {
            0: 'CONNECTING',
            1: 'OPEN',
            2: 'CLOSING',
            3: 'CLOSED'
        };
        console.log('\n🌐 WebSocket Status:');
        console.log('  State:', wsStates[splitScreenManager.logsWs.readyState]);
        console.log('  URL:', splitScreenManager.logsWs.url);
    } else {
        console.log('\n⚠️ WebSocket not initialized');
    }

    // Check computed styles
    const logsPanel = document.querySelector('.logs-panel');
    const logsPanelContent = document.querySelector('.logs-panel-content');

    if (logsPanel) {
        const panelStyles = window.getComputedStyle(logsPanel);
        console.log('\n🎨 Logs Panel Computed Styles:');
        console.log('  display:', panelStyles.display);
        console.log('  width:', panelStyles.width);
        console.log('  height:', panelStyles.height);
        console.log('  flex:', panelStyles.flex);
        console.log('  visibility:', panelStyles.visibility);
    }

    if (logsPanelContent) {
        const contentStyles = window.getComputedStyle(logsPanelContent);
        console.log('\n🎨 Logs Panel Content Computed Styles:');
        console.log('  display:', contentStyles.display);
        console.log('  width:', contentStyles.width);
        console.log('  height:', contentStyles.height);
        console.log('  overflow-y:', contentStyles.overflowY);
        console.log('  scrollHeight:', logsPanelContent.scrollHeight);
        console.log('  clientHeight:', logsPanelContent.clientHeight);
        console.log('  children count:', logsPanelContent.children.length);
    }

    // Check for errors
    console.log('\n🚨 Potential Issues:');
    let issuesFound = 0;

    if (!splitScreenManager.isActive) {
        console.warn('  ⚠️ Split-screen is not active. Click the Logs button to activate.');
        issuesFound++;
    }

    if (splitScreenManager.isActive && !splitScreenManager.logsWs) {
        console.error('  ❌ WebSocket not created despite split-screen being active');
        issuesFound++;
    }

    if (splitScreenManager.logsWs && splitScreenManager.logsWs.readyState !== 1) {
        console.error('  ❌ WebSocket is not OPEN');
        issuesFound++;
    }

    if (splitScreenManager.lineCount === 0 && splitScreenManager.isActive) {
        console.warn('  ⚠️ No log lines added yet. WebSocket may not have sent messages.');
        issuesFound++;
    }

    const logLines = document.querySelectorAll('.log-line');
    if (logLines.length > 0 && logsPanel && window.getComputedStyle(logsPanel).display === 'none') {
        console.error('  ❌ Log lines exist but panel is hidden (display: none)');
        issuesFound++;
    }

    if (issuesFound === 0) {
        console.log('  ✅ No obvious issues detected!');
    }

    // Helper functions
    console.log('\n💡 Available Helper Functions:');
    console.log('  window.testAddLog() - Add a test log line');
    console.log('  window.debugLogs() - Run this diagnostic again');
    console.log('  splitScreenManager.activate() - Activate split-screen');
    console.log('  splitScreenManager.clearLogs() - Clear all logs');

    console.log('\n✅ Diagnostic Complete\n');
})();

// Make it globally available
window.debugLogs = arguments.callee;
