import 'package:flutter_test/flutter_test.dart';
import 'package:hardwizchippy/main.dart';

void main() {
  testWidgets('App loads smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const HardWizChippyApp());

    // Verify the app title is present
    expect(find.text('HardWizChippy'), findsOneWidget);
  });
}
