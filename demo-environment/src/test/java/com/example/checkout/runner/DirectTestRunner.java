package com.example.checkout.runner;

import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.TagFilter;
import org.junit.platform.launcher.TestExecutionListener;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;
import org.junit.platform.launcher.listeners.SummaryGeneratingListener;
import org.junit.platform.launcher.listeners.TestExecutionSummary;

import java.io.PrintWriter;
import java.util.Set;

/**
 * IncidentOS Programmatic Direct Test Runner.
 *
 * Executes pre-approved test suites using the locally cached JUnit Platform Launcher API.
 * Operates strictly in-process without Gradle, Gradle daemons, TestWorker processes,
 * network sockets, or loopback connections.
 */
public class DirectTestRunner {

    private static final Set<String> APPROVED_SUITES = Set.of(
            "checkout-service-unit-tests",
            "checkout-service-regression-test",
            "payment-validator-tests"
    );

    public static void main(String[] args) {
        if (args.length != 1 || !APPROVED_SUITES.contains(args[0])) {
            System.err.println("[ERROR] Invalid or unapproved test suite: " + (args.length > 0 ? args[0] : "<none>"));
            System.err.println("Allowed test suites: " + APPROVED_SUITES);
            System.exit(2);
        }

        String suite = args[0];
        System.out.println("Starting IncidentOS Direct Test Runner for suite: " + suite);

        LauncherDiscoveryRequestBuilder requestBuilder = LauncherDiscoveryRequestBuilder.request();

        switch (suite) {
            case "checkout-service-unit-tests":
                // Standard unit tests: excludes known guest checkout regression
                requestBuilder
                        .selectors(DiscoverySelectors.selectPackage("com.example.checkout"))
                        .filters(TagFilter.excludeTags("regression"));
                break;
            case "checkout-service-regression-test":
                // Guest checkout regression reproduction test
                requestBuilder
                        .selectors(DiscoverySelectors.selectPackage("com.example.checkout"))
                        .filters(TagFilter.includeTags("regression"));
                break;
            case "payment-validator-tests":
                // PaymentValidator unit test suite
                requestBuilder
                        .selectors(DiscoverySelectors.selectClass("com.example.checkout.service.PaymentValidatorTest"));
                break;
            default:
                System.err.println("[ERROR] Unsupported suite: " + suite);
                System.exit(2);
        }

        LauncherDiscoveryRequest request = requestBuilder.build();
        Launcher launcher = LauncherFactory.create();

        SummaryGeneratingListener summaryListener = new SummaryGeneratingListener();
        launcher.registerTestExecutionListeners(summaryListener);

        launcher.registerTestExecutionListeners(new TestExecutionListener() {
            @Override
            public void executionStarted(TestIdentifier testIdentifier) {
                if (testIdentifier.isTest()) {
                    System.out.println("  [RUN] " + testIdentifier.getDisplayName());
                }
            }

            @Override
            public void executionFinished(TestIdentifier testIdentifier, org.junit.platform.engine.TestExecutionResult testExecutionResult) {
                if (testIdentifier.isTest()) {
                    System.out.println("  [" + testExecutionResult.getStatus() + "] " + testIdentifier.getDisplayName());
                }
            }
        });

        launcher.execute(request);

        TestExecutionSummary summary = summaryListener.getSummary();
        long found = summary.getTestsFoundCount();
        long succeeded = summary.getTestsSucceededCount();
        long failed = summary.getTestsFailedCount();
        long skipped = summary.getTestsSkippedCount();
        long aborted = summary.getTestsAbortedCount();
        long totalCompleted = succeeded + failed;

        System.out.println();
        System.out.println("--- JUnit Execution Summary ---");
        System.out.println("tests_found:     " + found);
        System.out.println("tests_succeeded: " + succeeded);
        System.out.println("tests_failed:    " + failed);
        System.out.println("tests_skipped:   " + skipped);
        System.out.println("tests_aborted:   " + aborted);
        System.out.println(totalCompleted + " tests completed, " + failed + " failed, " + skipped + " skipped");

        if (found == 0) {
            System.err.println("[ERROR] Zero tests discovered for suite: " + suite);
            System.exit(2);
        }

        if (failed > 0) {
            System.err.println();
            System.err.println("Failures (" + failed + "):");
            for (TestExecutionSummary.Failure f : summary.getFailures()) {
                System.err.println("FAIL: " + f.getTestIdentifier().getDisplayName() + " -> " + f.getException());
                f.getException().printStackTrace(new PrintWriter(System.err, true));
            }
            System.exit(1);
        }

        System.exit(0);
    }
}
