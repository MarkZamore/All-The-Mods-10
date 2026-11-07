import java.lang.instrument.Instrumentation;
import java.nio.file.*;
public class QaMenu {
 public static void premain(String output, Instrumentation instrumentation) {
  Thread t=new Thread(()->{
   int[] samples={0};
   Path log = Path.of(output).getParent().resolve("Minecraft/Personal/Instances/All The Mods 10/logs/latest.log");
   long startingStamp;
   try { startingStamp = Files.getLastModifiedTime(log).toMillis(); } catch(Exception e) { startingStamp = 0; }
   for(int i=0;i<1200;i++) {
    try {
     Thread.sleep(1000);
     if (!Files.exists(log) || Files.getLastModifiedTime(log).toMillis() <= startingStamp ||
         !Files.readString(log).contains("Reloading ResourceManager")) continue;
     Class<?> loaded = null;
     for (Class<?> candidate : instrumentation.getAllLoadedClasses()) {
      if (candidate.getName().equals("net.minecraft.client.Minecraft")) { loaded = candidate; break; }
     }
     if (loaded == null) continue;
     final Class<?> c = loaded;
     Object mc=c.getMethod("getInstance").invoke(null);
     c.getMethod("execute",Runnable.class).invoke(mc,(Runnable)()->{
      try {
       Object screen=c.getField("screen").get(mc);
       boolean title=false;
       for(Class<?> s=screen==null?null:screen.getClass();s!=null;s=s.getSuperclass())
        if(s.getName().equals("net.minecraft.client.gui.screens.TitleScreen"))title=true;
       if(title && c.getField("level").get(mc)==null && ++samples[0]>=3) {
        Files.writeString(Path.of(output),"{\"titleMenuSamples\":"+samples[0]+"}");
        c.getMethod("stop").invoke(mc);
       }
      }catch(Exception ignored){}
     });
    }catch(Throwable ignored){}
   }
  },"ATM10 QA menu observer");t.setDaemon(true);t.start();
 }
}
